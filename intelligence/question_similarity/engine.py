from __future__ import annotations

import hashlib
import math
import re
import uuid
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.core_exam import SyllabusTopic
from app.models.question_intel import (
    Question,
    QuestionCluster,
    QuestionEmbedding,
    QuestionPaper,
    QuestionSimilarity,
    QuestionTopic,
)

settings = get_settings()

_ST_MODEL = None
_ST_TRIED = False

TOKEN_RE = re.compile(r"[a-z0-9\+\-\*/\^=]+")


def _get_sentence_transformer():
    global _ST_MODEL, _ST_TRIED
    if _ST_TRIED:
        return _ST_MODEL
    _ST_TRIED = True
    if not getattr(settings, "USE_TRANSFORMER_EMBEDDINGS", False) and not settings.ALLOW_MODEL_DOWNLOAD:
        return None
    try:
        from sentence_transformers import SentenceTransformer

        _ST_MODEL = SentenceTransformer(
            settings.EMBEDDING_MODEL_NAME,
            local_files_only=not settings.ALLOW_MODEL_DOWNLOAD,
        )
    except Exception:
        _ST_MODEL = None
    return _ST_MODEL


def compute_text_embedding(text: str, dim: int = 384) -> list[float]:
    """
    Generates a normalized 384-dim embedding using SentenceTransformers when available locally,
    or a deterministic semantic hashing projection (word + character trigram n-grams) offline.
    """
    model = _get_sentence_transformer()
    if model is not None:
        vec = model.encode([text], normalize_embeddings=True)[0]
        return [float(x) for x in vec]

    clean = re.sub(r"\s+", " ", (text or "").lower()).strip()
    vec = np.zeros(dim, dtype=np.float32)

    words = TOKEN_RE.findall(clean)
    for w in words:
        h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vec[idx] += sign * 1.5

    # Character trigrams capture mathematical expressions and morphological overlap
    padded = f" {clean} "
    for i in range(max(0, len(padded) - 2)):
        tri = padded[i : i + 3]
        h = int(hashlib.blake2b(tri.encode("utf-8"), digest_size=8).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 3) & 1) == 0 else -1.0
        vec[idx] += sign * 0.4

    norm = float(np.linalg.norm(vec))
    if norm > 1e-9:
        vec = vec / norm
    return [round(float(x), 6) for x in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom <= 1e-9:
        return 0.0
    return float(np.dot(va, vb) / denom)


def classify_relationship(
    cosine_score: float,
    q_a_hash: str,
    q_b_hash: str,
    same_topic: bool,
    same_type: bool,
    diff_a: str,
    diff_b: str,
) -> tuple[str, float, str]:
    """
    Distinguishes between:
    - exact_duplicate
    - paraphrase
    - same_concept
    - same_pattern
    - difficulty_variation
    Uses vector similarity + metadata validation (never treats similar questions as automatically identical).
    """
    if q_a_hash == q_b_hash or cosine_score >= 0.985:
        meta = 1.0 if same_type else 0.75
        conf = round(0.8 * cosine_score + 0.2 * meta, 3)
        return (
            "exact_duplicate",
            meta,
            "Exact or near-verbatim text match verified via content hash and embedding similarity.",
        )

    if cosine_score >= 0.80 and same_topic and diff_a != diff_b:
        meta = 0.85 if same_type else 0.65
        return (
            "difficulty_variation",
            meta,
            f"Tests the same underlying concept at a different difficulty tier ({diff_a} vs {diff_b}).",
        )

    if cosine_score >= 0.78 and same_type:
        meta = 0.9 if same_topic else 0.7
        return (
            "paraphrase",
            meta,
            "High semantic overlap and matching question format indicate a paraphrased or re-numbered variant.",
        )

    if same_topic and cosine_score >= 0.42:
        meta = 0.85 if same_type else 0.7
        return (
            "same_concept",
            meta,
            "Shares the same syllabus concept with moderate structural similarity.",
        )

    if same_type and cosine_score >= 0.45:
        return (
            "same_pattern",
            0.7,
            "Follows a similar examination question pattern and response format.",
        )

    return (
        "same_concept" if same_topic else "same_pattern",
        0.5 if same_topic else 0.35,
        "Related structural or conceptual framing detected via vector similarity.",
    )


def ensure_question_embeddings(db: Session, questions: list[Question]) -> dict[uuid.UUID, list[float]]:
    existing = {
        e.question_id: e.embedding
        for e in db.query(QuestionEmbedding)
        .filter(QuestionEmbedding.question_id.in_([q.id for q in questions]))
        .all()
    } if questions else {}

    created_any = False
    for q in questions:
        if q.id not in existing:
            vec = compute_text_embedding(q.question_text, dim=settings.EMBEDDING_DIM)
            emb = QuestionEmbedding(
                question_id=q.id,
                model_name=settings.EMBEDDING_MODEL_NAME,
                model_version="1.0",
                embedding=vec,
            )
            db.add(emb)
            existing[q.id] = vec
            created_any = True

    if created_any:
        db.commit()
    return existing


def auto_classify_question_topic(
    db: Session,
    question: Question,
    exam_id: uuid.UUID,
    subject_id: uuid.UUID,
) -> SyllabusTopic | None:
    """Matches a question to the best SyllabusTopic using keyword overlap + embedding similarity."""
    from app.models.core_exam import ExamSubject, SyllabusVersion

    es = (
        db.query(ExamSubject)
        .filter(ExamSubject.exam_id == exam_id, ExamSubject.subject_id == subject_id)
        .first()
    )
    if not es:
        return None

    sv = (
        db.query(SyllabusVersion)
        .filter(SyllabusVersion.exam_subject_id == es.id, SyllabusVersion.is_active.is_(True))
        .first()
    )
    if not sv:
        return None

    topics = db.query(SyllabusTopic).filter(SyllabusTopic.syllabus_version_id == sv.id).all()
    if not topics:
        return None

    q_lower = question.question_text.lower()
    q_vec = compute_text_embedding(question.question_text)

    best_topic: SyllabusTopic | None = None
    best_score = -1.0
    for t in topics:
        kw_list = t.keywords_json or []
        kw_hits = sum(1 for kw in kw_list if kw.lower() in q_lower)
        topic_desc = f"{t.chapter_name} {t.topic_name} {' '.join(kw_list)}"
        sim = cosine_similarity(q_vec, compute_text_embedding(topic_desc))
        score = sim + 0.25 * min(kw_hits, 3)
        if score > best_score:
            best_score = score
            best_topic = t

    if best_topic:
        existing_link = (
            db.query(QuestionTopic)
            .filter(QuestionTopic.question_id == question.id, QuestionTopic.topic_id == best_topic.id)
            .first()
        )
        if not existing_link:
            db.add(
                QuestionTopic(
                    question_id=question.id,
                    topic_id=best_topic.id,
                    is_primary=True,
                    confidence=round(min(0.98, max(0.55, best_score)), 3),
                    assigned_by="nlp_classifier",
                )
            )
            db.commit()
    return best_topic


def find_similar_questions(
    db: Session,
    query_text: str | None = None,
    query_question_id: uuid.UUID | None = None,
    exam_id: uuid.UUID | None = None,
    subject_id: uuid.UUID | None = None,
    top_k: int = 8,
) -> list[dict[str, Any]]:
    paper_query = db.query(QuestionPaper).filter(
        QuestionPaper.is_deleted.is_(False),
        QuestionPaper.data_origin != "synthetic_dev",
    )
    if exam_id:
        paper_query = paper_query.filter(QuestionPaper.exam_id == exam_id)
    if subject_id:
        paper_query = paper_query.filter(QuestionPaper.subject_id == subject_id)
    papers = {p.id: p for p in paper_query.all()}
    if not papers:
        return []

    questions = (
        db.query(Question)
        .filter(
            Question.question_paper_id.in_(list(papers.keys())),
            Question.is_deleted.is_(False),
        )
        .all()
    )
    if not questions:
        return []

    embeddings = ensure_question_embeddings(db, questions)

    q_topics = {
        qt.question_id: qt.topic_id
        for qt in db.query(QuestionTopic)
        .filter(QuestionTopic.question_id.in_([q.id for q in questions]), QuestionTopic.is_primary.is_(True))
        .all()
    }
    topics = {
        t.id: t
        for t in db.query(SyllabusTopic).filter(SyllabusTopic.id.in_(list(q_topics.values()))).all()
    } if q_topics else {}

    anchor_q: Question | None = None
    if query_question_id:
        anchor_q = next((q for q in questions if q.id == query_question_id), None)
        if not anchor_q:
            anchor_q = db.query(Question).filter(Question.id == query_question_id).first()
        if anchor_q:
            anchor_vec = embeddings.get(anchor_q.id) or compute_text_embedding(anchor_q.question_text)
            anchor_hash = anchor_q.content_hash
            anchor_topic_id = q_topics.get(anchor_q.id)
            anchor_type = anchor_q.question_type
            anchor_diff = anchor_q.difficulty
        else:
            return []
    elif query_text:
        anchor_vec = compute_text_embedding(query_text)
        anchor_hash = hashlib.sha256(query_text.lower().strip().encode("utf-8")).hexdigest()
        anchor_topic_id = None
        anchor_type = ""
        anchor_diff = "medium"
    else:
        return []

    scored: list[dict[str, Any]] = []
    for cand in questions:
        if anchor_q and cand.id == anchor_q.id:
            continue
        cos = cosine_similarity(anchor_vec, embeddings[cand.id])
        same_topic = bool(anchor_topic_id and q_topics.get(cand.id) == anchor_topic_id)
        same_type = bool(anchor_type and cand.question_type == anchor_type)
        rel_type, meta_score, expl = classify_relationship(
            cos,
            anchor_hash,
            cand.content_hash,
            same_topic,
            same_type,
            anchor_diff,
            cand.difficulty,
        )
        combined = round(0.75 * max(0.0, cos) + 0.25 * meta_score, 3)
        p = papers[cand.question_paper_id]
        t = topics.get(q_topics.get(cand.id))
        scored.append(
            {
                "question_obj": cand,
                "paper_obj": p,
                "topic_obj": t,
                "cosine_score": round(cos, 3),
                "metadata_score": round(meta_score, 3),
                "combined_confidence": combined,
                "relationship_type": rel_type,
                "explanation": expl,
            }
        )

    scored.sort(key=lambda x: x["combined_confidence"], reverse=True)
    return scored[:top_k]


def cluster_questions_for_subject(
    db: Session,
    exam_id: uuid.UUID,
    subject_id: uuid.UUID,
) -> list[QuestionCluster]:
    papers = (
        db.query(QuestionPaper)
        .filter(
            QuestionPaper.exam_id == exam_id,
            QuestionPaper.subject_id == subject_id,
            QuestionPaper.is_deleted.is_(False),
            QuestionPaper.data_origin != "synthetic_dev",
        )
        .all()
    )
    if not papers:
        return []
    paper_map = {p.id: p for p in papers}
    questions = (
        db.query(Question)
        .filter(Question.question_paper_id.in_(list(paper_map.keys())), Question.is_deleted.is_(False))
        .all()
    )
    if len(questions) < 3:
        return []

    embeddings = ensure_question_embeddings(db, questions)
    matrix = np.asarray([embeddings[q.id] for q in questions], dtype=np.float32)
    n_clusters = max(2, min(10, len(questions) // 3))
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = km.fit_predict(matrix)

    # Clear prior clusters for this exam+subject
    db.query(QuestionCluster).filter(
        QuestionCluster.exam_id == exam_id, QuestionCluster.subject_id == subject_id
    ).delete()

    created: list[QuestionCluster] = []
    for cid in range(n_clusters):
        members = [q for q, lbl in zip(questions, labels) if int(lbl) == cid]
        if not members:
            continue
        years = sorted({paper_map[m.question_paper_id].year for m in members})
        avg_m = round(sum(float(m.marks) for m in members) / len(members), 2)
        sample_words = " ".join(members[0].question_text.split()[:8])
        cluster = QuestionCluster(
            exam_id=exam_id,
            subject_id=subject_id,
            cluster_label=f"Pattern Cluster #{cid + 1}",
            pattern_summary=f"Recurring structure around: '{sample_words}...'",
            question_count=len(members),
            avg_marks=avg_m,
            years_appeared_json=years,
        )
        db.add(cluster)
        db.flush()
        for m in members:
            m.cluster_id = cluster.id
        created.append(cluster)

    db.commit()
    return created
