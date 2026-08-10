"""محرّك بنود التغطية التأمينية.

المصدر: وثيقة الضمان الصحي الأساسية (مجلس الضمان الصحي التعاوني) — تطبيق 1 أكتوبر 2022.
كل حد مذكور هنا مأخوذ حرفيًا من الوثيقة، ورقم الصفحة مسجّل في "source_page"
عشان الموظف يقدر يرجع للمرجع، والـ AI ما يخترع أرقامًا من عنده.

الوثيقة تمثّل الحد الأدنى الإلزامي. فئات بوبا الأعلى تُبنى فوقها في TIERS.
"""

# ---------------------------------------------------------------------------
# فئات التأمين
# ---------------------------------------------------------------------------
# الوثيقة الأساسية سقفها السنوي 500,000 ريال (ص42). الفئات الأعلى ترفع السقف
# وبعض المنافع بمعامل. عدّل القيم حسب جداول منتجات بوبا الفعلية.

TIERS = {
    "Essential": {
        "label_ar": "أساسية",
        "annual_cap": 500_000,
        "benefit_multiplier": 1.0,
        "room_type": "غرفة مشتركة",
    },
    "Standard": {
        "label_ar": "قياسية",
        "annual_cap": 750_000,
        "benefit_multiplier": 1.5,
        "room_type": "غرفة مشتركة",
    },
    "Gold": {
        "label_ar": "ذهبية",
        "annual_cap": 1_000_000,
        "benefit_multiplier": 2.0,
        "room_type": "غرفة خاصة",
    },
    "VIP": {
        "label_ar": "بلاتينية",
        "annual_cap": 2_000_000,
        "benefit_multiplier": 3.0,
        "room_type": "جناح",
    },
}

DEFAULT_TIER = "Essential"

# المنافع اللي سقفها منصوص عليه بالوثيقة ولا يرتفع برفع الفئة
FIXED_BY_REGULATION = {"DENTAL_BASIC", "DENTAL_ENDO", "OPTICAL", "CIRCUMCISION", "CONTRACEPTION"}


# ---------------------------------------------------------------------------
# البنود
# ---------------------------------------------------------------------------
# annual_limit  : الحد الأقصى خلال مدة الوثيقة (ريال)
# copay_rate    : نسبة تحمّل المستفيد
# copay_cap     : أقصى مبلغ يتحمّله المستفيد
# pre_approval  : تحتاج موافقة مسبقة قبل تقديم الخدمة
# typical_visit : المدى الطبيعي لزيارة واحدة — يُستخدم لكشف الشذوذ
# icd_prefixes  : بادئات ICD-10 المرتبطة بالبند
# procedure     : بادئات أكواد الإجراءات (ADA للأسنان مثلاً)

BENEFITS = {
    "DENTAL_BASIC": {
        "name_ar": "طب الأسنان الأساسي والوقائي",
        "name_en": "Basic & preventive dentistry",
        "annual_limit": 1_200,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": False,
        "typical_visit": (100, 3_000),
        "icd_prefixes": ["K00", "K01", "K02", "K03", "K05", "K06"],
        "procedure": ["D0", "D1", "D2", "D3", "D4"],
        "source_page": 43,
    },
    "DENTAL_ENDO": {
        "name_ar": "علاج القنوات الجذرية وحالات الأسنان الطارئة",
        "name_en": "Root canal & dental emergencies",
        "annual_limit": 800,
        "copay_rate": 0.20,
        "copay_cap": None,
        "pre_approval": False,
        "typical_visit": (300, 800),
        "icd_prefixes": ["K04"],
        "procedure": ["D33"],
        "source_page": 43,
    },
    "OPTICAL": {
        "name_ar": "النظارات الطبية",
        "name_en": "Prescription glasses",
        "annual_limit": 400,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": False,
        "age_max": 14,  # لمن بعمر 14 سنة فأقل
        "typical_visit": (100, 400),
        "icd_prefixes": ["H52"],
        "procedure": ["V20", "V21"],
        "source_page": 43,
    },
    "MATERNITY": {
        "name_ar": "نفقات الحمل والولادة",
        "name_en": "Pregnancy & childbirth",
        "annual_limit": 15_000,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": False,
        "gender": "Female",
        "typical_visit": (300, 15_000),
        "icd_prefixes": ["O0", "O1", "O2", "O3", "O4", "O6", "O7", "O8", "Z34"],
        "procedure": [],
        "source_page": 43,
    },
    "DIALYSIS": {
        "name_ar": "الغسيل الكلوي",
        "name_en": "Renal dialysis",
        "annual_limit": 180_000,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": True,
        "typical_visit": (500, 3_000),
        "icd_prefixes": ["N18", "N19", "Z49"],
        "procedure": [],
        "source_page": 43,
    },
    "KIDNEY_TRANSPLANT": {
        "name_ar": "زراعة الكلى",
        "name_en": "Kidney transplant",
        "annual_limit": 250_000,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": True,
        "typical_visit": (50_000, 250_000),
        "icd_prefixes": ["Z94.0", "T86.1"],
        "procedure": [],
        "source_page": 43,
    },
    "PSYCHIATRIC": {
        "name_ar": "علاج الحالات النفسية",
        "name_en": "Psychiatric care",
        "annual_limit": 50_000,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": False,
        "typical_visit": (200, 2_500),
        "icd_prefixes": ["F"],
        "procedure": [],
        "source_page": 43,
    },
    "REPATRIATION": {
        "name_ar": "إعادة جثمان المتوفى",
        "name_en": "Repatriation of remains",
        "annual_limit": 10_000,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": True,
        "typical_visit": (3_000, 10_000),
        "icd_prefixes": [],
        "procedure": [],
        "source_page": 43,
    },
    "HEARING_AIDS": {
        "name_ar": "السماعات الطبية",
        "name_en": "Hearing aids",
        "annual_limit": 6_000,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": True,
        "typical_visit": (1_000, 6_000),
        "icd_prefixes": ["H90", "H91"],
        "procedure": [],
        "source_page": 43,
    },
    "HEART_VALVE": {
        "name_ar": "حالات التليّف في صمامات القلب",
        "name_en": "Heart valve disease",
        "annual_limit": 150_000,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": True,
        "typical_visit": (5_000, 150_000),
        "icd_prefixes": ["I34", "I35", "I36", "I37"],
        "procedure": [],
        "source_page": 43,
    },
    "ORGAN_DONATION": {
        "name_ar": "عملية التبرع بالأعضاء للمتبرع",
        "name_en": "Organ donation procedure",
        "annual_limit": 50_000,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": True,
        "typical_visit": (10_000, 50_000),
        "icd_prefixes": ["Z52"],
        "procedure": [],
        "source_page": 44,
    },
    "ALZHEIMER": {
        "name_ar": "مرضى الزهايمر",
        "name_en": "Alzheimer's care",
        "annual_limit": 15_000,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": False,
        "typical_visit": (300, 5_000),
        "icd_prefixes": ["G30", "F00"],
        "procedure": [],
        "source_page": 44,
    },
    "AUTISM": {
        "name_ar": "حالات التوحد",
        "name_en": "Autism care",
        "annual_limit": 50_000,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": False,
        "typical_visit": (300, 5_000),
        "icd_prefixes": ["F84"],
        "procedure": [],
        "source_page": 44,
    },
    "NEWBORN_SCREENING": {
        "name_ar": "البرنامج الوطني للفحص المبكر لحديثي الولادة",
        "name_en": "National newborn screening",
        "annual_limit": 100_000,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": False,
        "typical_visit": (200, 5_000),
        "icd_prefixes": ["Z00.1", "P"],
        "procedure": [],
        "source_page": 44,
    },
    "DISABILITY": {
        "name_ar": "حالات الإعاقة",
        "name_en": "Disability care",
        "annual_limit": 100_000,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": True,
        "typical_visit": (500, 20_000),
        "icd_prefixes": [],
        "procedure": [],
        "source_page": 44,
    },
    "BARIATRIC": {
        "name_ar": "جراحة معالجة السمنة المفرطة",
        "name_en": "Bariatric surgery",
        "annual_limit": 15_000,
        "copay_rate": 0.20,
        "copay_cap": 1_000,  # الحد الأقصى للمشاركة بالدفع
        "pre_approval": True,
        "typical_visit": (8_000, 15_000),
        "icd_prefixes": ["E66"],
        "procedure": [],
        "source_page": 44,
    },
    "CIRCUMCISION": {
        "name_ar": "حالات الختان للذكور",
        "name_en": "Male circumcision",
        "annual_limit": 500,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": False,
        "gender": "Male",
        "typical_visit": (200, 500),
        "icd_prefixes": ["Z41.2"],
        "procedure": [],
        "source_page": 44,
    },
    "CONTRACEPTION": {
        "name_ar": "موانع الحمل",
        "name_en": "Contraceptives",
        "annual_limit": 1_500,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": False,
        "typical_visit": (50, 700),
        "icd_prefixes": ["Z30"],
        "procedure": [],
        "source_page": 44,
    },
    "INPATIENT_ROOM": {
        "name_ar": "الإقامة والإعاشة اليومية بالمستشفى",
        "name_en": "Daily inpatient room & board",
        "annual_limit": None,  # يخضع للسقف السنوي العام
        "daily_limit": 600,
        "companion_daily_limit": 150,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": True,
        "typical_visit": (600, 60_000),
        "icd_prefixes": [],
        "procedure": [],
        "source_page": 43,
    },
    "EMERGENCY": {
        "name_ar": "خدمات العلاج الطارئة",
        "name_en": "Emergency treatment",
        "annual_limit": None,
        "copay_rate": 0.0,  # لا يُستقطع تحمّل للطوارئ
        "copay_cap": None,
        "pre_approval": False,
        "typical_visit": (200, 20_000),
        "icd_prefixes": [],
        "procedure": [],
        "source_page": 42,
    },
    "PRIMARY_CARE": {
        "name_ar": "الرعاية الصحية الأولية",
        "name_en": "Primary care consultation",
        "annual_limit": None,
        "copay_rate": 0.0,
        "copay_cap": None,
        "pre_approval": False,
        "typical_visit": (50, 800),
        "icd_prefixes": ["J0", "J1", "R50", "Z00"],
        "procedure": [],
        "source_page": 39,
    },
}

# البنود المستثناة صراحة (تُرفض دائمًا) — أمثلة شائعة، وسّعها من فصل الاستثناءات
EXCLUSIONS = {
    "COSMETIC": {
        "name_ar": "العمليات التجميلية غير العلاجية",
        "icd_prefixes": ["Z41.1"],
        "keywords": ["cosmetic", "botox", "تجميل", "بوتوكس", "شد الوجه"],
    },
    "FERTILITY": {
        "name_ar": "علاج العقم وأطفال الأنابيب",
        "icd_prefixes": ["N97", "Z31"],
        "keywords": ["ivf", "fertility", "أطفال الأنابيب", "العقم"],
    },
}


# ---------------------------------------------------------------------------
# التصنيف
# ---------------------------------------------------------------------------

def _matches(code, prefixes):
    if not code or not prefixes:
        return False
    upper = str(code).upper().replace(" ", "")
    return any(upper.startswith(prefix.upper()) for prefix in prefixes)


def classify_benefit(diagnosis_code=None, procedure_code=None, description=None, claim_type=None):
    """يحدد بند التغطية من كود التشخيص أو الإجراء أو الوصف."""
    text = " ".join(str(part or "").lower() for part in (description, claim_type))

    for code, rule in EXCLUSIONS.items():
        if _matches(diagnosis_code, rule.get("icd_prefixes")) or any(
            keyword in text for keyword in rule.get("keywords", [])
        ):
            return code, "excluded"

    # الإجراء أدق من التشخيص لما يكون موجودًا
    for code, rule in BENEFITS.items():
        if _matches(procedure_code, rule.get("procedure")):
            return code, "covered"

    best = None
    for code, rule in BENEFITS.items():
        for prefix in rule.get("icd_prefixes", []):
            if _matches(diagnosis_code, [prefix]):
                # نفضّل البادئة الأطول (K04 أدق من K)
                if best is None or len(prefix) > best[1]:
                    best = (code, len(prefix))
    if best:
        return best[0], "covered"

    if "dental" in text or "أسنان" in text:
        return "DENTAL_BASIC", "covered"
    if "emergency" in text or "طوارئ" in text:
        return "EMERGENCY", "covered"

    return "PRIMARY_CARE", "covered"


# ---------------------------------------------------------------------------
# التقييم
# ---------------------------------------------------------------------------

def effective_limit(benefit_code, tier=DEFAULT_TIER):
    """الحد الفعلي للبند حسب فئة المستفيد."""
    rule = BENEFITS[benefit_code]
    base = rule.get("annual_limit")
    if base is None:
        return None
    if benefit_code in FIXED_BY_REGULATION:
        return base  # حد نظامي ثابت لا يتأثر بالفئة
    multiplier = TIERS.get(tier, TIERS[DEFAULT_TIER])["benefit_multiplier"]
    return round(base * multiplier, 2)


def detect_amount_anomaly(amount, benefit_code, tier=DEFAULT_TIER):
    """يكشف المبالغ الشاذة بمقارنتها بالمدى الطبيعي وبالحد النظامي.

    مثال: 57,000 ريال لفحص أسنان دوري حده 1,200 ريال — شذوذ حرج.
    """
    rule = BENEFITS[benefit_code]
    low, high = rule.get("typical_visit", (0, float("inf")))
    limit = effective_limit(benefit_code, tier)

    reference = limit if limit is not None else high
    if not reference:
        return None

    ratio = amount / reference if reference else 0

    if amount > reference * 10:
        severity = "critical"
    elif amount > reference * 3:
        severity = "high"
    elif amount > high:
        severity = "medium"
    else:
        return None

    return {
        "severity": severity,
        "ratio": round(ratio, 1),
        "amount": amount,
        "reference": reference,
        "typical_range": [low, high],
        "message_en": (
            f"SAR {amount:,.2f} is {ratio:.1f}x the {rule['name_en']} ceiling of "
            f"SAR {reference:,.2f}. A typical visit costs between SAR {low:,.0f} "
            f"and SAR {high:,.0f}."
        ),
        "message_ar": (
            f"المبلغ {amount:,.2f} ريال يعادل {ratio:.1f} ضعف حد \"{rule['name_ar']}\" "
            f"البالغ {reference:,.2f} ريال. الزيارة الاعتيادية تتراوح بين "
            f"{low:,.0f} و {high:,.0f} ريال."
        ),
    }


def _result(benefit_code, name_ar, decision, amount, payable, reasons,
            anomaly=None, copay=0.0, limit=None, used=0.0, tier=DEFAULT_TIER,
            annual_remaining=None, source_page=None, name_en=None):
    """يبني نتيجة بنفس المفاتيح دائمًا مهما كان مسار القرار."""
    tier_config = TIERS.get(tier, TIERS[DEFAULT_TIER])
    return {
        "benefit_code": benefit_code,
        "benefit_name": name_ar,
        "benefit_name_en": name_en or name_ar,
        "source_page": source_page,
        "tier": tier,
        "decision": decision,
        "claimed": round(amount, 2),
        "payable": round(payable, 2),
        "member_share": round(amount - payable, 2),
        "copay": round(copay, 2),
        "limit": limit,
        "remaining": None if limit is None else round(max(0.0, limit - used), 2),
        "annual_cap": tier_config["annual_cap"],
        "annual_remaining": annual_remaining,
        "reasons": reasons,
        "anomaly": anomaly,
    }


def evaluate_claim(
    amount,
    diagnosis_code=None,
    procedure_code=None,
    description=None,
    claim_type=None,
    tier=DEFAULT_TIER,
    member_age=None,
    member_gender=None,
    used_this_year=0.0,
    annual_used=0.0,
    has_pre_approval=False,
):
    """القرار الكامل لمطالبة واحدة مقابل بنود الوثيقة.

    يرجع decision من: approve / partial / pre_approval_required / reject
    """
    benefit_code, coverage = classify_benefit(
        diagnosis_code, procedure_code, description, claim_type
    )

    if coverage == "excluded":
        rule = EXCLUSIONS[benefit_code]
        return _result(benefit_code, rule["name_ar"], "reject", amount, 0.0, tier=tier,
            reasons=[{
                "code": "NOT_COVERED",
                "text_en": f"{rule['name_ar']} is excluded from the policy.",
                "text_ar": f"البند \"{rule['name_ar']}\" مستثنى من التغطية.",
            }])

    rule = BENEFITS[benefit_code]
    tier_config = TIERS.get(tier, TIERS[DEFAULT_TIER])
    limit = effective_limit(benefit_code, tier)
    reasons = []
    decision = "approve"

    # 1) شروط الأهلية (عمر / جنس)
    if rule.get("age_max") is not None and member_age is not None and member_age > rule["age_max"]:
        return _result(benefit_code, rule["name_ar"], "reject", amount, 0.0, tier=tier,
            limit=limit, source_page=rule["source_page"], name_en=rule["name_en"],
            reasons=[{
                "code": "AGE_INELIGIBLE",
                "text_en": f"{rule['name_en']} is limited to members aged "
                           f"{rule['age_max']} and under; this member is {member_age}.",
                "text_ar": f"منفعة \"{rule['name_ar']}\" مقصورة على عمر "
                           f"{rule['age_max']} سنة فأقل، وعمر المستفيد {member_age}.",
            }])

    if rule.get("gender") and member_gender and rule["gender"].lower() != str(member_gender).lower():
        return _result(benefit_code, rule["name_ar"], "reject", amount, 0.0, tier=tier,
            limit=limit, source_page=rule["source_page"], name_en=rule["name_en"],
            reasons=[{
                "code": "GENDER_INELIGIBLE",
                "text_en": f"{rule['name_en']} does not apply to this member.",
                "text_ar": f"منفعة \"{rule['name_ar']}\" لا تنطبق على هذا المستفيد.",
            }])

    # 2) كشف الشذوذ في المبلغ
    anomaly = detect_amount_anomaly(amount, benefit_code, tier)
    if anomaly:
        reasons.append({
            "code": "AMOUNT_ANOMALY",
            "text_en": anomaly["message_en"],
            "text_ar": anomaly["message_ar"],
        })
        if anomaly["severity"] in ("critical", "high"):
            decision = "reject"

    # 3) الرصيد المتبقي من حد البند
    payable = amount
    if limit is not None:
        remaining = max(0.0, limit - used_this_year)
        if remaining <= 0:
            return _result(benefit_code, rule["name_ar"], "reject", amount, 0.0,
                tier=tier, limit=limit, used=used_this_year, anomaly=anomaly,
                source_page=rule["source_page"], name_en=rule["name_en"],
                reasons=reasons + [{
                    "code": "LIMIT_EXHAUSTED",
                    "text_en": f"The annual {rule['name_en']} limit of SAR {limit:,.2f} "
                               f"is fully used (SAR {used_this_year:,.2f} claimed).",
                    "text_ar": f"حد \"{rule['name_ar']}\" السنوي البالغ {limit:,.2f} ريال "
                               f"مستنفد بالكامل (المستخدم {used_this_year:,.2f} ريال).",
                }])

        if amount > remaining:
            payable = remaining
            decision = "partial" if decision == "approve" else decision
            reasons.append({
                "code": "LIMIT_PARTIAL",
                "text_en": f"Only SAR {remaining:,.2f} remains of the SAR {limit:,.2f} "
                           f"annual {rule['name_en']} limit.",
                "text_ar": f"المتبقي {remaining:,.2f} ريال فقط من حد \"{rule['name_ar']}\" "
                           f"السنوي البالغ {limit:,.2f} ريال.",
            })

    # 4) السقف السنوي العام للفئة
    annual_cap = tier_config["annual_cap"]
    annual_remaining = max(0.0, annual_cap - annual_used)
    if payable > annual_remaining:
        payable = annual_remaining
        decision = "partial" if decision in ("approve", "partial") else decision
        reasons.append({
            "code": "ANNUAL_CAP",
            "text_en": f"Only SAR {annual_remaining:,.2f} remains of the "
                       f"{tier} annual cap of SAR {annual_cap:,.2f}.",
            "text_ar": f"المتبقي {annual_remaining:,.2f} ريال من السقف السنوي "
                       f"لفئة {tier} البالغ {annual_cap:,.2f} ريال.",
        })

    # 5) الموافقة المسبقة
    if rule.get("pre_approval") and not has_pre_approval and decision != "reject":
        decision = "pre_approval_required"
        reasons.append({
            "code": "PRE_APPROVAL_REQUIRED",
            "text_en": f"{rule['name_en']} requires pre-approval before the service "
                       f"is provided (policy p.{rule['source_page']}).",
            "text_ar": f"منفعة \"{rule['name_ar']}\" تتطلب موافقة مسبقة قبل تقديم "
                       f"الخدمة (الوثيقة ص{rule['source_page']}).",
        })

    # 6) نسبة التحمّل
    copay = 0.0
    if rule.get("copay_rate"):
        copay = payable * rule["copay_rate"]
        if rule.get("copay_cap") is not None:
            copay = min(copay, rule["copay_cap"])
        reasons.append({
            "code": "COPAY",
            "text_en": f"Member co-payment of {rule['copay_rate']:.0%} "
                       f"(SAR {copay:,.2f}) applies.",
            "text_ar": f"نسبة تحمّل {rule['copay_rate']:.0%} على المستفيد "
                       f"({copay:,.2f} ريال).",
        })

    insurer_pays = round(payable - copay, 2)

    if decision == "approve" and not reasons:
        reasons.append({
            "code": "WITHIN_LIMITS",
            "text_en": f"Fully covered under {rule['name_en']} "
                       f"(policy p.{rule['source_page']}).",
            "text_ar": f"مغطاة بالكامل تحت بند \"{rule['name_ar']}\" "
                       f"(الوثيقة ص{rule['source_page']}).",
        })

    return _result(
        benefit_code, rule["name_ar"], decision, amount, insurer_pays, reasons,
        anomaly=anomaly, copay=copay, limit=limit, used=used_this_year, tier=tier,
        annual_remaining=round(annual_remaining, 2),
        source_page=rule["source_page"], name_en=rule["name_en"],
    )
