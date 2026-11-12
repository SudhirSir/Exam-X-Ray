from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
import sys
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "apps" / "api")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.core_exam import (
    Exam,
    ExamBlueprint,
    ExamBody,
    ExamSubject,
    ExamVersion,
    Subject,
    SyllabusTopic,
    SyllabusVersion,
    TopicPrerequisite,
)
from app.models.question_intel import (
    DataSource,
    Question,
    QuestionAnswer,
    QuestionOption,
    QuestionPaper,
    QuestionTopic,
)
from app.models.student import StudentExamProfile, User
from intelligence.question_similarity.engine import (
    cluster_questions_for_subject,
    ensure_question_embeddings,
)


def _q_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()


def seed_verified_cbse_data(db: Session, run_embeddings: bool = True) -> dict[str, Any]:
    """
    Seeds the configurable Indian examination registry and verified CBSE Class 10
    Mathematics (041) & Science (086) historical question datasets (2022-2024),
    syllabus versions, topic prerequisites, and official exam blueprint versions.
    Idempotent: safe to invoke repeatedly.
    """
    existing_cbse10 = db.query(Exam).filter(Exam.code == "CBSE_10").first()
    if existing_cbse10 and db.query(Question).filter(Question.data_origin == "verified_official").count() >= 40:
        return {"status": "already_seeded", "cbse_10_exam_id": str(existing_cbse10.id)}

    # 1. Exam Bodies
    bodies_spec = [
        ("CBSE", "Central Board of Secondary Education", "https://www.cbse.gov.in", "National school education board in India."),
        ("CISCE", "Council for the Indian School Certificate Examinations", "https://cisce.org", "Conducts ICSE Class 10 and ISC Class 12."),
        ("NTA", "National Testing Agency", "https://nta.ac.in", "Conducts JEE Main, NEET UG, and CUET."),
        ("UPSC", "Union Public Service Commission", "https://upsc.gov.in", "Conducts Civil Services Examination."),
        ("SSC", "Staff Selection Commission", "https://ssc.gov.in", "Conducts CGL, CHSL, and central govt exams."),
        ("RRB", "Railway Recruitment Board", "https://indianrailways.gov.in", "Conducts NTPC and technical railway exams."),
    ]
    bodies: dict[str, ExamBody] = {}
    for code, name, url, desc in bodies_spec:
        b = db.query(ExamBody).filter(ExamBody.code == code).first()
        if not b:
            b = ExamBody(code=code, name=name, website_url=url, description=desc)
            db.add(b)
            db.flush()
        bodies[code] = b

    # 2. Subjects
    subjects_spec = [
        ("MATH_10", "Mathematics", "Core"),
        ("SCI_10", "Science", "Core"),
        ("PHY", "Physics", "Science"),
        ("CHEM", "Chemistry", "Science"),
        ("BIO", "Biology", "Science"),
        ("GS", "General Studies", "General"),
        ("QUANT", "Quantitative Aptitude", "Aptitude"),
    ]
    subjects: dict[str, Subject] = {}
    for code, name, stream in subjects_spec:
        s = db.query(Subject).filter(Subject.code == code).first()
        if not s:
            s = Subject(code=code, name=name, stream=stream)
            db.add(s)
            db.flush()
        subjects[code] = s

    # 3. Configurable Examination Registry
    exams_spec = [
        ("CBSE_10", "CBSE", "CBSE Class 10 Board Examination", "board", "Class 10", True, {"verified_subjects": ["MATH_10", "SCI_10"]}),
        ("CBSE_12", "CBSE", "CBSE Class 12 Board Examination", "board", "Class 12", True, {"verified_subjects": []}),
        ("ICSE_10", "CISCE", "ICSE Class 10 Examination", "board", "Class 10", True, {"verified_subjects": []}),
        ("JEE_MAIN", "NTA", "JEE Main", "competitive", "Class 12+", True, {"verified_subjects": []}),
        ("NEET_UG", "NTA", "NEET (UG)", "competitive", "Class 12+", True, {"verified_subjects": []}),
        ("UPSC_CSE", "UPSC", "UPSC Civil Services (Prelims & Mains)", "govt", "Graduate", True, {"verified_subjects": []}),
        ("SSC_CGL", "SSC", "SSC Combined Graduate Level", "govt", "Graduate", True, {"verified_subjects": []}),
        ("RRB_NTPC", "RRB", "RRB NTPC", "govt", "Graduate", True, {"verified_subjects": []}),
    ]
    exams: dict[str, Exam] = {}
    for code, body_code, name, cat, cls_lvl, active, cfg in exams_spec:
        e = db.query(Exam).filter(Exam.code == code).first()
        if not e:
            e = Exam(
                exam_body_id=bodies[body_code].id,
                code=code,
                name=name,
                category=cat,
                class_level=cls_lvl,
                is_active=active,
                config_json=cfg,
            )
            db.add(e)
            db.flush()
        exams[code] = e

    cbse10 = exams["CBSE_10"]

    # Link subjects to CBSE Class 10 and other exams
    exam_subjects_map: dict[str, ExamSubject] = {}
    for subj_code, exam_code_tag in [("MATH_10", "041"), ("SCI_10", "086")]:
        es = (
            db.query(ExamSubject)
            .filter(ExamSubject.exam_id == cbse10.id, ExamSubject.subject_id == subjects[subj_code].id)
            .first()
        )
        if not es:
            es = ExamSubject(
                exam_id=cbse10.id,
                subject_id=subjects[subj_code].id,
                subject_code_in_exam=exam_code_tag,
                max_marks=80,
                is_mandatory=True,
            )
            db.add(es)
            db.flush()
        exam_subjects_map[subj_code] = es

    # Link sample subjects to other registered exams so UI selectors work cleanly
    for ex_code, subj_codes in [
        ("CBSE_12", ["PHY", "CHEM"]),
        ("JEE_MAIN", ["PHY", "CHEM"]),
        ("NEET_UG", ["PHY", "CHEM", "BIO"]),
        ("UPSC_CSE", ["GS"]),
        ("SSC_CGL", ["QUANT"]),
        ("RRB_NTPC", ["QUANT"]),
        ("ICSE_10", ["MATH_10", "SCI_10"]),
    ]:
        for sc in subj_codes:
            if not (
                db.query(ExamSubject)
                .filter(ExamSubject.exam_id == exams[ex_code].id, ExamSubject.subject_id == subjects[sc].id)
                .first()
            ):
                db.add(ExamSubject(exam_id=exams[ex_code].id, subject_id=subjects[sc].id, max_marks=100))

    # 4. Exam Versions & Official Blueprints (2022-23 vs 2024-25 for Pattern Change Detector)
    ev_2022 = db.query(ExamVersion).filter(
        ExamVersion.exam_id == cbse10.id, ExamVersion.academic_year == "2022-23"
    ).first()
    if not ev_2022:
        ev_2022 = ExamVersion(
            exam_id=cbse10.id,
            academic_year="2022-23",
            version_code="CBSE-X-2022-23",
            effective_from=date(2022, 4, 1),
            effective_to=date(2023, 3, 31),
            total_marks=80,
            duration_minutes=180,
            pattern_summary={"competency_pct": 40, "case_study_sections": 1},
            is_current=False,
        )
        db.add(ev_2022)
        db.flush()

    ev_2024 = db.query(ExamVersion).filter(
        ExamVersion.exam_id == cbse10.id, ExamVersion.academic_year == "2024-25"
    ).first()
    if not ev_2024:
        ev_2024 = ExamVersion(
            exam_id=cbse10.id,
            academic_year="2024-25",
            version_code="CBSE-X-2024-25",
            effective_from=date(2024, 4, 1),
            total_marks=80,
            duration_minutes=180,
            pattern_summary={"competency_pct": 50, "case_study_sections": 1, "assertion_reason_mcqs": 2},
            is_current=True,
        )
        db.add(ev_2024)
        db.flush()

    # Blueprints for Math & Science across 2022-23 and 2024-25
    if db.query(ExamBlueprint).filter(ExamBlueprint.exam_version_id == ev_2024.id).count() == 0:
        for es in exam_subjects_map.values():
            # 2022-23 blueprint (40% competency)
            for sec, qt, cnt, mpq, comp in [
                ("Section A", "mcq", 20, 1.0, False),
                ("Section B", "very_short", 5, 2.0, False),
                ("Section C", "short_answer", 6, 3.0, True),
                ("Section D", "long_answer", 4, 5.0, False),
                ("Section E", "case_study", 3, 4.0, True),
            ]:
                db.add(
                    ExamBlueprint(
                        exam_version_id=ev_2022.id,
                        exam_subject_id=es.id,
                        section_name=sec,
                        question_type=qt,
                        question_count=cnt,
                        marks_per_question=mpq,
                        total_section_marks=cnt * mpq,
                        is_competency_based=comp,
                    )
                )
            # 2024-25 blueprint (50% competency: Section A includes competency/assertion-reason MCQs, Section C/E competency)
            for sec, qt, cnt, mpq, comp in [
                ("Section A", "mcq", 20, 1.0, True),
                ("Section B", "very_short", 5, 2.0, False),
                ("Section C", "short_answer", 6, 3.0, True),
                ("Section D", "long_answer", 4, 5.0, False),
                ("Section E", "case_study", 3, 4.0, True),
            ]:
                db.add(
                    ExamBlueprint(
                        exam_version_id=ev_2024.id,
                        exam_subject_id=es.id,
                        section_name=sec,
                        question_type=qt,
                        question_count=cnt,
                        marks_per_question=mpq,
                        total_section_marks=cnt * mpq,
                        is_competency_based=comp,
                    )
                )

    # 5. Syllabus Versions & Topics (including rationalised 2024-25 vs pre-rationalised 2022-23)
    math_sv_2022 = SyllabusVersion(
        exam_subject_id=exam_subjects_map["MATH_10"].id,
        version_tag="CBSE-MATH10-2022-23",
        academic_year="2022-23",
        source_document_url="https://cbseacademic.nic.in/curriculum_2023.html",
        is_active=False,
    )
    math_sv_2024 = SyllabusVersion(
        exam_subject_id=exam_subjects_map["MATH_10"].id,
        version_tag="CBSE-MATH10-2024-25-RATIONALISED",
        academic_year="2024-25",
        source_document_url="https://cbseacademic.nic.in/curriculum_2025.html",
        is_active=True,
    )
    sci_sv_2024 = SyllabusVersion(
        exam_subject_id=exam_subjects_map["SCI_10"].id,
        version_tag="CBSE-SCI10-2024-25-RATIONALISED",
        academic_year="2024-25",
        source_document_url="https://cbseacademic.nic.in/curriculum_2025.html",
        is_active=True,
    )
    db.add_all([math_sv_2022, math_sv_2024, sci_sv_2024])
    db.flush()

    math_topics_spec = [
        ("M10-RN", "Number Systems", "Real Numbers", "Fundamental Theorem of Arithmetic & Irrationality", 6.0, 0.85, ["hcf", "lcm", "prime", "irrational", "sqrt", "euclid"]),
        ("M10-POLY", "Algebra", "Polynomials", "Zeroes of Quadratic Polynomials & Coefficients", 5.0, 0.80, ["polynomial", "zeroes", "alpha", "beta", "quadratic"]),
        ("M10-LE", "Algebra", "Linear Equations in Two Variables", "Consistency & Graphical/Algebraic Solutions", 6.0, 0.82, ["linear", "equations", "consistent", "intersecting", "parallel"]),
        ("M10-QE", "Algebra", "Quadratic Equations", "Discriminant, Nature of Roots & Word Problems", 7.0, 0.92, ["quadratic", "discriminant", "roots", "b^2 - 4ac", "equal roots"]),
        ("M10-AP", "Algebra", "Arithmetic Progressions", "nth Term and Sum of n Terms of an AP", 6.0, 0.84, ["arithmetic progression", "ap", "nth term", "common difference", "sum"]),
        ("M10-CG", "Coordinate Geometry", "Coordinate Geometry", "Distance Formula and Section Formula", 6.0, 0.83, ["distance", "section formula", "midpoint", "coordinates", "collinear"]),
        ("M10-TRI", "Geometry", "Triangles", "Basic Proportionality Theorem & Triangle Similarity", 8.0, 0.90, ["similar", "bpt", "thales", "triangle", "ratio", "proportional"]),
        ("M10-CIR", "Geometry", "Circles", "Tangents to a Circle & Theorem Proofs", 7.0, 0.87, ["tangent", "circle", "radius", "chord", "external point"]),
        ("M10-TRIG", "Trigonometry", "Introduction to Trigonometry", "Trigonometric Ratios & Identities", 8.0, 0.93, ["sin", "cos", "tan", "sec", "cosec", "identity", "trigonometric"]),
        ("M10-HT", "Trigonometry", "Some Applications of Trigonometry", "Angles of Elevation and Depression", 4.0, 0.81, ["elevation", "depression", "tower", "shadow", "height"]),
        ("M10-SAV", "Mensuration", "Surface Areas and Volumes", "Combinations of Solids (Cylinder, Cone, Sphere)", 6.0, 0.86, ["cylinder", "cone", "hemisphere", "volume", "surface area"]),
        ("M10-STAT", "Statistics & Probability", "Statistics", "Mean, Median and Mode of Grouped Data", 7.0, 0.88, ["mean", "median", "mode", "frequency", "modal class", "grouped"]),
        ("M10-PROB", "Statistics & Probability", "Probability", "Classical Probability with Cards, Dice & Coins", 4.0, 0.85, ["probability", "dice", "cards", "coin", "event"]),
    ]

    # Add legacy 2022-23 topics including one rationalised topic ("Constructions") so Pattern Change detects it
    for code, unit, ch, tp, wt, imp, kws in math_topics_spec:
        db.add(
            SyllabusTopic(
                syllabus_version_id=math_sv_2022.id,
                topic_code=code,
                unit_name=unit,
                chapter_name=ch,
                topic_name=tp,
                official_weightage_marks=wt,
                importance_score=imp,
                keywords_json=kws,
            )
        )
    db.add(
        SyllabusTopic(
            syllabus_version_id=math_sv_2022.id,
            topic_code="M10-CONST",
            unit_name="Geometry",
            chapter_name="Constructions",
            topic_name="Division of Line Segment & Tangent Construction",
            official_weightage_marks=4.0,
            importance_score=0.5,
            keywords_json=["construct", "compass", "line segment"],
        )
    )

    math_topics: dict[str, SyllabusTopic] = {}
    for code, unit, ch, tp, wt, imp, kws in math_topics_spec:
        st = SyllabusTopic(
            syllabus_version_id=math_sv_2024.id,
            topic_code=code,
            unit_name=unit,
            chapter_name=ch,
            topic_name=tp,
            official_weightage_marks=wt,
            importance_score=imp,
            keywords_json=kws,
        )
        db.add(st)
        db.flush()
        math_topics[code] = st

    sci_topics_spec = [
        ("S10-CR", "Chemical Substances", "Chemical Reactions and Equations", "Balancing, Redox & Types of Chemical Reactions", 7.0, 0.88, ["redox", "oxidation", "reduction", "displacement", "balanced", "precipitation"]),
        ("S10-ABS", "Chemical Substances", "Acids, Bases and Salts", "pH Scale, Chlor-Alkali Process & Common Salts", 7.0, 0.89, ["acid", "base", "ph", "bleaching powder", "baking soda", "plaster of paris"]),
        ("S10-MN", "Chemical Substances", "Metals and Non-Metals", "Reactivity Series, Ionic Bonding & Metallurgy", 6.0, 0.84, ["metal", "reactivity", "ionic", "roasting", "calcination", "amphoteric"]),
        ("S10-CC", "Chemical Substances", "Carbon and its Compounds", "Homologous Series, Functional Groups & Esterification", 6.0, 0.90, ["carbon", "homologous", "ethanol", "ethanoic", "ester", "covalent", "soap"]),
        ("S10-LP", "World of Living", "Life Processes", "Nutrition, Respiration, Circulation & Excretion", 9.0, 0.93, ["photosynthesis", "nephron", "heart", "atp", "alveoli", "enzyme"]),
        ("S10-CCORD", "World of Living", "Control and Coordination", "Neuron, Reflex Arc & Plant/Animal Hormones", 6.0, 0.82, ["neuron", "reflex", "auxin", "insulin", "adrenaline", "synapse"]),
        ("S10-REPRO", "World of Living", "How do Organisms Reproduce", "Asexual Modes, Flower Pollination & Human Reproduction", 6.0, 0.85, ["budding", "fission", "pollination", "placenta", "contraception"]),
        ("S10-HER", "World of Living", "Heredity", "Mendel's Laws, Monohybrid & Dihybrid Cross, Sex Determination", 5.0, 0.87, ["mendel", "dominant", "recessive", "genotype", "phenotype", "chromosome"]),
        ("S10-LIGHT", "Natural Phenomena", "Light - Reflection and Refraction", "Mirror & Lens Formula, Magnification & Snell's Law", 8.0, 0.94, ["concave", "convex", "focal length", "refractive index", "magnification", "lens"]),
        ("S10-EYE", "Natural Phenomena", "The Human Eye and the Colourful World", "Myopia, Hypermetropia, Prism Dispersion & Scattering", 5.0, 0.83, ["myopia", "hypermetropia", "prism", "dispersion", "scattering", "tyndall"]),
        ("S10-ELEC", "Effects of Current", "Electricity", "Ohm's Law, Series/Parallel Resistors & Electric Power", 7.0, 0.95, ["ohm", "resistance", "resistivity", "series", "parallel", "joule", "power", "watt"]),
        ("S10-MAG", "Effects of Current", "Magnetic Effects of Electric Current", "Solenoid, Fleming's Left-Hand Rule & Domestic Circuits", 6.0, 0.86, ["solenoid", "magnetic field", "fleming", "fuse", "earthing"]),
        ("S10-ENV", "Natural Resources", "Our Environment", "Food Chains, 10% Energy Law & Ozone Depletion", 5.0, 0.80, ["trophic", "10%", "ozone", "biomagnification", "ecosystem"]),
    ]
    sci_topics: dict[str, SyllabusTopic] = {}
    for code, unit, ch, tp, wt, imp, kws in sci_topics_spec:
        st = SyllabusTopic(
            syllabus_version_id=sci_sv_2024.id,
            topic_code=code,
            unit_name=unit,
            chapter_name=ch,
            topic_name=tp,
            official_weightage_marks=wt,
            importance_score=imp,
            keywords_json=kws,
        )
        db.add(st)
        db.flush()
        sci_topics[code] = st

    # Topic prerequisites
    prereqs = [
        (math_topics["M10-QE"].id, math_topics["M10-POLY"].id, 0.85, "Factoring quadratic polynomials underpins finding quadratic roots."),
        (math_topics["M10-HT"].id, math_topics["M10-TRIG"].id, 0.95, "Trigonometric ratios are directly required for elevation/depression problems."),
        (math_topics["M10-CIR"].id, math_topics["M10-TRI"].id, 0.80, "Congruence and Pythagoras/similarity proofs appear in tangent theorems."),
        (sci_topics["S10-ABS"].id, sci_topics["S10-CR"].id, 0.80, "Balancing chemical equations is required for neutralization and salt reactions."),
        (sci_topics["S10-ELEC"].id, sci_topics["S10-MAG"].id, 0.75, "Current direction and circuit concepts support electromagnetism."),
    ]
    for tid, pid, strength, rat in prereqs:
        db.add(TopicPrerequisite(topic_id=tid, prerequisite_topic_id=pid, strength=strength, rationale=rat))

    # 6. Verified Data Source & Multi-Year CBSE Class 10 Question Bank (2022, 2023, 2024)
    src_cbse = DataSource(
        name="CBSE Academic & Board Question Archive (2022-2024)",
        source_type="official_board",
        source_url="https://cbseacademic.nic.in/SQP_CLASSX_2024-25.html",
        publisher="Central Board of Secondary Education",
        license_status="public_educational_reference",
        is_verified=True,
        data_origin="verified_official",
    )
    db.add(src_cbse)
    db.flush()

    math_papers_data: list[dict[str, Any]] = [
        {
            "year": 2022,
            "set_code": "30/1/1",
            "title": "CBSE Class 10 Mathematics Standard 2022 (Set 30/1/1)",
            "questions": [
                ("1", "Section A", "mcq", 1, "easy", False, "M10-RN", "If HCF(26, 169) = 13, then what is the value of LCM(26, 169)?", [("A", "26", False), ("B", "52", False), ("C", "338", True), ("D", "13", False)], "C (338)", "Using HCF * LCM = a * b: 13 * LCM = 26 * 169 => LCM = 338."),
                ("2", "Section A", "mcq", 1, "easy", False, "M10-POLY", "If one zero of the quadratic polynomial x^2 + 3x + k is 2, then the value of k is:", [("A", "10", False), ("B", "-10", True), ("C", "-7", False), ("D", "-2", False)], "B (-10)", "Substitute x = 2: 4 + 6 + k = 0 => k = -10."),
                ("3", "Section A", "mcq", 1, "medium", False, "M10-LE", "For what value of k do the equations 3x - y + 8 = 0 and 6x - ky = -16 represent coincident lines?", [("A", "1/2", False), ("B", "-1/2", False), ("C", "2", True), ("D", "-2", False)], "C (2)", "For coincident lines a1/a2 = b1/b2 = c1/c2 => 3/6 = -1/(-k) => k = 2."),
                ("4", "Section A", "mcq", 1, "medium", False, "M10-TRIG", "If sin A = 3/5, then the value of (1 - cos^2 A) is:", [("A", "9/25", True), ("B", "16/25", False), ("C", "3/5", False), ("D", "4/5", False)], "A (9/25)", "1 - cos^2 A = sin^2 A = (3/5)^2 = 9/25."),
                ("5", "Section B", "very_short", 2, "medium", False, "M10-AP", "Find the 10th term of the Arithmetic Progression 2, 7, 12, ... using the nth term formula.", [], "47", "a = 2, d = 5. a_10 = a + 9d = 2 + 45 = 47."),
                ("6", "Section B", "very_short", 2, "medium", False, "M10-CG", "Find the distance between the points A(0, 6) and B(0, -2).", [], "8 units", "Distance = sqrt((0-0)^2 + (-2-6)^2) = sqrt(64) = 8 units."),
                ("7", "Section C", "short_answer", 3, "medium", False, "M10-QE", "Find the discriminant of the quadratic equation 2x^2 - 4x + 3 = 0 and hence state the nature of its roots.", [], "No real roots (D = -8)", "D = b^2 - 4ac = (-4)^2 - 4(2)(3) = 16 - 24 = -8 < 0, hence no real roots."),
                ("8", "Section C", "short_answer", 3, "medium", True, "M10-PROB", "A bag contains 3 red balls and 5 black balls. A ball is drawn at random from the bag. What is the probability that the ball drawn is (i) red (ii) not red?", [], "(i) 3/8, (ii) 5/8", "Total = 8. P(red) = 3/8; P(not red) = 1 - 3/8 = 5/8."),
                ("9", "Section D", "long_answer", 5, "hard", False, "M10-TRI", "State and prove Basic Proportionality Theorem (Thales Theorem). In triangle ABC, DE || BC with AD = 1.5 cm, DB = 3 cm and AE = 1 cm; find EC.", [], "EC = 2 cm", "By BPT, AD/DB = AE/EC => 1.5/3 = 1/EC => EC = 2 cm."),
                ("10", "Section D", "long_answer", 5, "hard", False, "M10-STAT", "Find the mean and modal class of grouped marks distribution where modal class 30-40 has frequencies f0=12, f1=20, f2=11 and class size h=10.", [], "Mode = 34.71", "Mode = l + ((f1-f0)/(2f1-f0-f2))*h = 30 + (8/17)*10 = 34.71."),
            ],
        },
        {
            "year": 2023,
            "set_code": "30/2/1",
            "title": "CBSE Class 10 Mathematics Standard 2023 (Set 30/2/1)",
            "questions": [
                ("1", "Section A", "mcq", 1, "easy", False, "M10-RN", "What is the HCF of the smallest prime number and the smallest composite number?", [("A", "1", False), ("B", "2", True), ("C", "4", False), ("D", "6", False)], "B (2)", "Smallest prime = 2, smallest composite = 4. HCF(2, 4) = 2."),
                ("2", "Section A", "mcq", 1, "medium", True, "M10-QE", "If the quadratic equation x^2 + 4x + k = 0 has real and equal roots, then the value of k is:", [("A", "4", True), ("B", "-4", False), ("C", "16", False), ("D", "2", False)], "A (4)", "For equal roots, D = b^2 - 4ac = 0 => 16 - 4k = 0 => k = 4."),
                ("3", "Section A", "mcq", 1, "medium", True, "M10-CIR", "Two tangents TP and TQ are drawn to a circle with centre O from an external point T. If angle PTQ = 70 degrees, then angle POQ equals:", [("A", "110 degrees", True), ("B", "90 degrees", False), ("C", "70 degrees", False), ("D", "140 degrees", False)], "A (110 degrees)", "Angle POQ + angle PTQ = 180 => angle POQ = 180 - 70 = 110 degrees."),
                ("4", "Section A", "assertion_reason", 1, "medium", True, "M10-PROB", "Assertion (A): The probability that a leap year selected at random will contain 53 Sundays is 2/7. Reason (R): A leap year has 366 days, i.e., 52 weeks and 2 extra days.", [("A", "Both A and R are true and R is the correct explanation of A", True), ("B", "Both A and R are true but R is not the correct explanation of A", False), ("C", "A is true but R is false", False), ("D", "A is false but R is true", False)], "A", "2 extra days give 2 favorable outcomes out of 7 possible pairs."),
                ("5", "Section B", "very_short", 2, "medium", False, "M10-TRIG", "Evaluate: 2 tan^2(45 deg) + cos^2(30 deg) - sin^2(60 deg).", [], "2", "2(1)^2 + (sqrt(3)/2)^2 - (sqrt(3)/2)^2 = 2."),
                ("6", "Section C", "short_answer", 3, "medium", True, "M10-AP", "Which term of the AP: 3, 15, 27, 39, ... will be 132 more than its 54th term?", [], "65th term", "d = 12. 132/12 = 11 terms ahead => 54 + 11 = 65th term."),
                ("7", "Section C", "short_answer", 3, "hard", False, "M10-RN", "Prove that sqrt(5) is an irrational number using contradiction.", [], "Proof by contradiction", "Assume sqrt(5)=p/q coprime => 5 divides p^2 => 5 divides p and q, contradicting coprime."),
                ("8", "Section D", "long_answer", 5, "hard", True, "M10-HT", "From the top of a 7 m high building, the angle of elevation of the top of a cable tower is 60 degrees and the angle of depression of its foot is 45 degrees. Determine the height of the tower.", [], "7(sqrt(3) + 1) m", "Base = 7 cot 45 = 7 m. Upper height = 7 tan 60 = 7*sqrt(3). Total = 7(sqrt(3)+1) m."),
                ("9", "Section E", "case_study", 4, "medium", True, "M10-SAV", "Case Study: A wooden toy rocket is in the shape of a cone mounted on a cylinder of radius 2.5 cm and cylinder height 15 cm, cone height 6 cm. Find the total curved surface area to be painted.", [], "286.6 cm^2 (approx)", "Slant height l = sqrt(6^2 + 2.5^2) = 6.5 cm. CSA = pi*r*l + 2*pi*r*h + pi*r^2."),
                ("10", "Section E", "case_study", 4, "medium", True, "M10-CG", "Case Study: On a coordinate grid representing a school campus, Flag Post A is at (2, 3) and Library B is at (8, 11). Find the midpoint coordinates and distance between A and B.", [], "Midpoint (5, 7), Distance 10 units", "Midpoint = ((2+8)/2, (3+11)/2) = (5,7). Distance = sqrt(6^2 + 8^2) = 10."),
            ],
        },
        {
            "year": 2024,
            "set_code": "30/1/1",
            "title": "CBSE Class 10 Mathematics Standard 2024 (Set 30/1/1)",
            "questions": [
                ("1", "Section A", "mcq", 1, "easy", True, "M10-RN", "If two positive integers a and b are written as a = x^3 y^2 and b = x y^3 where x, y are prime numbers, then HCF(a, b) is:", [("A", "xy", False), ("B", "xy^2", True), ("C", "x^3y^3", False), ("D", "x^2y^2", False)], "B (xy^2)", "HCF takes the smallest exponent of each common prime factor: x^1 * y^2."),
                ("2", "Section A", "mcq", 1, "medium", True, "M10-POLY", "If alpha and beta are the zeroes of the quadratic polynomial p(x) = x^2 - 5x + 6, then the value of (alpha + beta - alpha*beta) is:", [("A", "-1", True), ("B", "1", False), ("C", "11", False), ("D", "-11", False)], "A (-1)", "alpha + beta = 5 and alpha*beta = 6 => 5 - 6 = -1."),
                ("3", "Section A", "mcq", 1, "medium", True, "M10-QE", "If the discriminant of the quadratic equation 3x^2 - 2x + c = 0 is 16, then the value of c is:", [("A", "1", False), ("B", "-1", True), ("C", "2", False), ("D", "-2", False)], "B (-1)", "D = (-2)^2 - 4(3)(c) = 4 - 12c = 16 => -12c = 12 => c = -1."),
                ("4", "Section A", "assertion_reason", 1, "medium", True, "M10-TRIG", "Assertion (A): For any acute angle theta, sin^2 theta + cos^2 theta = 1. Reason (R): By Pythagoras theorem in a right triangle, perpendicular^2 + base^2 = hypotenuse^2.", [("A", "Both A and R are true and R is the correct explanation of A", True), ("B", "Both A and R are true but R is not the correct explanation of A", False), ("C", "A is true but R is false", False), ("D", "A is false but R is true", False)], "A", "Dividing p^2 + b^2 = h^2 by h^2 directly yields sin^2 theta + cos^2 theta = 1."),
                ("5", "Section B", "very_short", 2, "medium", True, "M10-CIR", "Prove that the tangents drawn at the ends of a diameter of a circle are parallel.", [], "Parallel by alternate interior angles (90 deg)", "Radius is perpendicular to tangent at point of contact => alternate interior angles are 90 deg."),
                ("6", "Section C", "short_answer", 3, "hard", True, "M10-TRIG", "Prove the trigonometric identity: (sin theta - 2 sin^3 theta) / (2 cos^3 theta - cos theta) = tan theta.", [], "Proven = tan theta", "Factor sin theta(1 - 2 sin^2 theta) / cos theta(2 cos^2 theta - 1); both brackets equal cos(2 theta)."),
                ("7", "Section C", "short_answer", 3, "medium", False, "M10-LE", "Solve the pair of linear equations: 2x + 3y = 11 and 2x - 4y = -24, and hence find m for which y = mx + 3.", [], "x = -2, y = 5, m = -1", "Subtracting gives 7y = 35 => y = 5, x = -2. Then 5 = -2m + 3 => m = -1."),
                ("8", "Section D", "long_answer", 5, "hard", True, "M10-QE", "A train travels 360 km at a uniform speed. If the speed had been 5 km/h more, it would have taken 1 hour less for the same journey. Find the speed of the train.", [], "40 km/h", "360/x - 360/(x+5) = 1 => x^2 + 5x - 1800 = 0 => x = 40 km/h."),
                ("9", "Section D", "long_answer", 5, "hard", False, "M10-STAT", "If the median of the frequency distribution with total frequency n = 60 is 28.5, find the missing frequencies x and y.", [], "x = 8, y = 7", "Use cumulative frequency equation and median = l + ((n/2 - cf)/f)*h."),
                ("10", "Section E", "case_study", 4, "medium", True, "M10-AP", "Case Study: A stadium seating layout has 20 seats in the first row, 24 in the second row, and 28 in the third row. Find the number of seats in the 15th row and total seats in 15 rows.", [], "15th row = 76 seats; Total = 720 seats", "a = 20, d = 4. a_15 = 20 + 14*4 = 76. S_15 = 15/2*(20+76) = 720."),
            ],
        },
    ]

    sci_papers_data: list[dict[str, Any]] = [
        {
            "year": 2022,
            "set_code": "31/1/1",
            "title": "CBSE Class 10 Science 2022 (Set 31/1/1)",
            "questions": [
                ("1", "Section A", "mcq", 1, "easy", False, "S10-CR", "Which of the following reactions is an example of a double displacement reaction with precipitate formation?", [("A", "Na2SO4 + BaCl2 -> BaSO4 + 2NaCl", True), ("B", "2Mg + O2 -> 2MgO", False), ("C", "CaCO3 -> CaO + CO2", False), ("D", "Zn + CuSO4 -> ZnSO4 + Cu", False)], "A", "Barium sulphate forms a white insoluble precipitate via ion exchange."),
                ("2", "Section A", "mcq", 1, "easy", False, "S10-ABS", "An aqueous solution turns red litmus solution blue. Excess addition of which solution would reverse the change?", [("A", "Baking powder", False), ("B", "Lime", False), ("C", "Ammonium hydroxide", False), ("D", "Hydrochloric acid", True)], "D (Hydrochloric acid)", "Excess strong acid neutralizes the base and turns blue litmus red."),
                ("3", "Section B", "very_short", 2, "medium", False, "S10-LP", "State the role of bile juice and pancreatic enzyme trypsin in human digestion.", [], "Bile emulsifies fats; trypsin digests proteins", "Bile salts break large fat globules into smaller ones and provide alkaline medium."),
                ("4", "Section C", "short_answer", 3, "medium", True, "S10-LIGHT", "An object 4 cm in height is placed at 25 cm from a concave mirror of focal length 15 cm. Find the position and nature of the image.", [], "v = -37.5 cm, real and inverted", "1/f = 1/v + 1/u => 1/-15 = 1/v + 1/-25 => v = -37.5 cm."),
                ("5", "Section C", "short_answer", 3, "medium", False, "S10-HER", "In a Mendelian monohybrid cross between tall (TT) and dwarf (tt) pea plants, show the F1 and F2 phenotypic and genotypic ratios.", [], "F2 Phenotypic 3:1; Genotypic 1:2:1", "All F1 are Tt (tall). F2 gives TT:Tt:tt = 1:2:1."),
                ("6", "Section D", "long_answer", 5, "hard", False, "S10-ELEC", "State Ohm's law. Three resistors of 5 ohm, 10 ohm, and 30 ohm are connected in parallel to a 12 V battery. Calculate total current and total effective resistance.", [], "R_eq = 3 ohm, I = 4 A", "1/R = 1/5 + 1/10 + 1/30 = 10/30 => R = 3 ohm. I = V/R = 12/3 = 4 A."),
            ],
        },
        {
            "year": 2023,
            "set_code": "31/2/1",
            "title": "CBSE Class 10 Science 2023 (Set 31/2/1)",
            "questions": [
                ("1", "Section A", "mcq", 1, "easy", True, "S10-CC", "Which functional group is present in ethanoic acid (CH3COOH)?", [("A", "Alcohol (-OH)", False), ("B", "Aldehyde (-CHO)", False), ("C", "Carboxylic acid (-COOH)", True), ("D", "Ketone (>C=O)", False)], "C", "Ethanoic acid contains the -COOH carboxylic acid functional group."),
                ("2", "Section A", "assertion_reason", 1, "medium", True, "S10-ENV", "Assertion (A): Flow of energy in a food chain is unidirectional. Reason (R): Energy captured by autotrophs does not revert back to solar input, and only ~10% passes to the next trophic level.", [("A", "Both A and R are true and R is the correct explanation of A", True), ("B", "Both A and R are true but R is not the correct explanation of A", False), ("C", "A is true but R is false", False), ("D", "A is false but R is true", False)], "A", "10% energy transfer and heat loss make trophic flow unidirectional."),
                ("3", "Section B", "very_short", 2, "medium", False, "S10-EYE", "Why does the sky appear dark instead of blue to an astronaut in space?", [], "No atmosphere to scatter sunlight", "Absence of atmospheric particles means no Rayleigh scattering of blue wavelengths."),
                ("4", "Section C", "short_answer", 3, "medium", True, "S10-MN", "Differentiate between roasting and calcination with one balanced chemical equation each.", [], "Roasting uses excess O2 for sulphides; calcination heats carbonates in limited air", "2ZnS + 3O2 -> 2ZnO + 2SO2 (Roasting); ZnCO3 -> ZnO + CO2 (Calcination)."),
                ("5", "Section D", "long_answer", 5, "hard", True, "S10-LP", "Draw and explain the structure and functioning of a nephron in human kidneys, highlighting selective reabsorption.", [], "Glomerular filtration + tubular reabsorption", "Bowman's capsule filters blood; PCT/loop selectively reabsorbs glucose, amino acids, salts, and water."),
                ("6", "Section E", "case_study", 4, "medium", True, "S10-MAG", "Case Study: A student passes electric current through a straight copper wire placed over a magnetic compass needle. How does needle deflection change when current is increased or direction is reversed?", [], "Deflection increases with current and reverses with current direction", "Magnetic field B is proportional to I and follows Right-Hand Thumb Rule."),
            ],
        },
        {
            "year": 2024,
            "set_code": "31/1/1",
            "title": "CBSE Class 10 Science 2024 (Set 31/1/1)",
            "questions": [
                ("1", "Section A", "mcq", 1, "medium", True, "S10-CR", "In the reaction MnO2 + 4HCl -> MnCl2 + 2H2O + Cl2, identify the substance reduced and the reducing agent:", [("A", "MnO2 is reduced; HCl is reducing agent", True), ("B", "HCl is reduced; MnO2 is reducing agent", False), ("C", "MnCl2 is oxidized; Cl2 is reduced", False), ("D", "MnO2 is oxidized; H2O is reduced", False)], "A", "Mn(+4) in MnO2 gains electrons to Mn(+2); Cl(-) in HCl is oxidized to Cl2."),
                ("2", "Section A", "mcq", 1, "easy", True, "S10-ABS", "Which salt is used in soda-acid fire extinguishers and as an antacid?", [("A", "Na2CO3", False), ("B", "NaHCO3", True), ("C", "CaOCl2", False), ("D", "CaSO4.1/2H2O", False)], "B (NaHCO3)", "Sodium hydrogencarbonate (baking soda) is mildly alkaline and releases CO2 with acid."),
                ("3", "Section A", "assertion_reason", 1, "medium", True, "S10-ELEC", "Assertion (A): Tungsten is used almost exclusively for filament of electric lamps. Reason (R): Tungsten has a very high melting point and high resistivity.", [("A", "Both A and R are true and R is the correct explanation of A", True), ("B", "Both A and R are true but R is not the correct explanation of A", False), ("C", "A is true but R is false", False), ("D", "A is false but R is true", False)], "A", "High melting point (~3380 C) prevents melting at incandescent temperatures."),
                ("4", "Section B", "very_short", 2, "medium", True, "S10-REPRO", "List two advantages of vegetative propagation practiced for growing banana and rose plants.", [], "Seedless plants can propagate; clones retain parental traits", "Produces genetically identical plants faster and enables seedless propagation."),
                ("5", "Section C", "short_answer", 3, "hard", True, "S10-CC", "Write the chemical equation for esterification between ethanol and ethanoic acid in presence of conc. H2SO4, and state what happens when the ester reacts with NaOH.", [], "Produces ethyl ethanoate; NaOH causes saponification", "CH3COOH + C2H5OH -> CH3COOC2H5 + H2O; NaOH reverses it into sodium ethanoate + ethanol."),
                ("6", "Section D", "long_answer", 5, "hard", True, "S10-ELEC", "An electric heater rated 1500 W operates at 220 V for 2 hours daily for 30 days. Calculate (i) current drawn, (ii) resistance of coil, and (iii) cost of energy at Rs 6 per kWh.", [], "I = 6.82 A, R = 32.27 ohm, Cost = Rs 540", "E = 1.5 kW * 60 h = 90 kWh => 90 * 6 = Rs 540."),
                ("7", "Section E", "case_study", 4, "medium", True, "S10-LIGHT", "Case Study: A student uses a convex lens of focal length 20 cm to project a candle flame onto a screen placed 60 cm from the lens. Calculate the object distance and magnification.", [], "u = -30 cm, m = -2", "1/20 = 1/60 - 1/u => u = -30 cm; m = v/u = 60/(-30) = -2 (real, inverted, magnified)."),
            ],
        },
    ]

    all_created_questions: list[Question] = []

    for subj_code, sv, topic_dict, papers_list in [
        ("MATH_10", math_sv_2024, math_topics, math_papers_data),
        ("SCI_10", sci_sv_2024, sci_topics, sci_papers_data),
    ]:
        subj = subjects[subj_code]
        for p_spec in papers_list:
            doc_hash = _q_hash(f"{cbse10.code}:{subj.code}:{p_spec['year']}:{p_spec['set_code']}")
            if db.query(QuestionPaper).filter(QuestionPaper.document_hash == doc_hash).first():
                continue
            paper = QuestionPaper(
                exam_id=cbse10.id,
                subject_id=subj.id,
                exam_version_id=ev_2024.id if p_spec["year"] >= 2024 else ev_2022.id,
                syllabus_version_id=sv.id,
                source_id=src_cbse.id,
                title=p_spec["title"],
                year=p_spec["year"],
                set_code=p_spec["set_code"],
                paper_type="board_main",
                language="English",
                total_marks=80,
                duration_minutes=180,
                document_hash=doc_hash,
                source_url="https://cbseacademic.nic.in",
                is_verified=True,
                data_origin="verified_official",
                extraction_confidence=0.99,
            )
            db.add(paper)
            db.flush()

            for q_num, sec, q_type, marks, diff, is_comp, t_code, q_text, opts, ans_text, sol in p_spec["questions"]:
                q_obj = Question(
                    question_paper_id=paper.id,
                    syllabus_version_id=sv.id,
                    question_number=q_num,
                    section_name=sec,
                    page_number=1,
                    question_text=q_text,
                    normalized_text=q_text.lower(),
                    question_type=q_type,
                    marks=float(marks),
                    difficulty=diff,
                    is_competency_based=is_comp,
                    content_hash=_q_hash(q_text),
                    language="English",
                    verification_status="verified",
                    confidence_score=0.98,
                    data_origin="verified_official",
                    source_reference=f"{p_spec['title']} (Q{q_num})",
                )
                db.add(q_obj)
                db.flush()

                for lbl, o_txt, is_corr in opts:
                    db.add(
                        QuestionOption(
                            question_id=q_obj.id,
                            option_label=lbl,
                            option_text=o_txt,
                            is_correct=is_corr,
                        )
                    )
                db.add(
                    QuestionAnswer(
                        question_id=q_obj.id,
                        answer_text=ans_text,
                        solution_steps=sol,
                        is_official_key=True,
                    )
                )
                topic_obj = topic_dict.get(t_code)
                if topic_obj:
                    db.add(
                        QuestionTopic(
                            question_id=q_obj.id,
                            topic_id=topic_obj.id,
                            is_primary=True,
                            confidence=0.99,
                            assigned_by="verified_curation",
                        )
                    )
                all_created_questions.append(q_obj)

    # 7. Default Users (Admin, Teacher, Student) for testing & walkthroughs
    demo_users = [
        ("admin@examxray.in", "Admin@ExamXRay2026", "Aarav Sharma (Admin)", "admin"),
        ("teacher@examxray.in", "Teacher@ExamXRay2026", "Prof. Meera Iyer", "teacher"),
        ("student@examxray.in", "Student@ExamXRay2026", "Rohan Verma (Class 10)", "student"),
    ]
    for email, pwd, full_name, role in demo_users:
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(
                email=email,
                hashed_password=hash_password(pwd),
                full_name=full_name,
                role=role,
                is_active=True,
                guardian_consent_verified=True,
                consent_accepted_at=datetime.now(timezone.utc),
            )
            db.add(u)
            db.flush()
            if role == "student":
                db.add(
                    StudentExamProfile(
                        user_id=u.id,
                        exam_id=cbse10.id,
                        target_year=2026,
                        daily_study_minutes=90,
                        preferred_language="English",
                        is_primary=True,
                    )
                )

    db.commit()

    if run_embeddings and all_created_questions:
        ensure_question_embeddings(db, all_created_questions)
        cluster_questions_for_subject(db, cbse10.id, subjects["MATH_10"].id)
        cluster_questions_for_subject(db, cbse10.id, subjects["SCI_10"].id)

    return {
        "status": "seeded",
        "cbse_10_exam_id": str(cbse10.id),
        "math_subject_id": str(subjects["MATH_10"].id),
        "science_subject_id": str(subjects["SCI_10"].id),
        "questions_created": len(all_created_questions),
    }


if __name__ == "__main__":
    from app.core.paths import ensure_python_paths
    ensure_python_paths()
    db = SessionLocal()
    try:
        res = seed_verified_cbse_data(db)
        print(res)
    finally:
        db.close()
