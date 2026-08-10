-- ============================================================================
-- Claim Readiness Platform — extension data
-- ============================================================================
-- Run schema_upgrade.py FIRST (it creates the tables), then run this file:
--
--     python schema_upgrade.py
--     sqlite3 database/claimDB.db < database/claim_extension.sql
--
-- Everything below is real data you control. Edit the values to match your
-- own test accounts. Re-running the file is safe (INSERT OR REPLACE / IGNORE).
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 1. Insurance tier for every member
-- ----------------------------------------------------------------------------
-- Tier must be one of: Essential, Standard, Gold, VIP.
-- The tier controls the annual cap and the benefit multiplier used by
-- policy_rules.py. Dental and optical limits stay fixed by regulation.

INSERT OR REPLACE INTO MemberPolicy
    (user_ID, Tier, PolicyNumber, PolicyStart, PolicyEnd, InsuranceCompany)
VALUES
    (1, 'Gold',      '22367668', '2026-01-01', '2026-12-31', 'Bupa'),
    (2, 'Standard',  '22367669', '2026-01-01', '2026-12-31', 'Bupa'),
    (3, 'Essential', '22367670', '2026-01-01', '2026-12-31', 'Bupa');


-- ----------------------------------------------------------------------------
-- 2. Family links   ***  FILL THIS IN YOURSELF  ***
-- ----------------------------------------------------------------------------
-- HeadUserID   = the policy holder (head of family)
-- MemberUserID = the dependent
-- Relationship = Spouse | Son | Daughter | Father | Mother
--
-- Nothing is inserted by default: your three accounts are unrelated test users,
-- and inventing relationships between them would put fake data on the reviewer's
-- screen. Uncomment and edit once you decide who is related to whom.
--
-- INSERT OR IGNORE INTO FamilyLinks (HeadUserID, MemberUserID, Relationship) VALUES
--     (1, 2, 'Spouse'),
--     (1, 3, 'Daughter');


-- ----------------------------------------------------------------------------
-- 3. Data-sharing consent
-- ----------------------------------------------------------------------------
-- ShareWithHead = 0 hides this member's details from the head of family.
-- ShareHistory  = 0 hides their medical history as well.
-- Only members aged 18+ may set these to 0; member_profile.py enforces that.
-- Default for everyone is 1 (sharing allowed), set by schema_upgrade.py.
--
-- To let one adult dependent withhold their data:
-- UPDATE DataSharingConsent SET ShareWithHead = 0, ShareHistory = 0 WHERE user_ID = 3;


-- ----------------------------------------------------------------------------
-- 4. Medical history   ***  FILL THIS IN YOURSELF  ***
-- ----------------------------------------------------------------------------
-- IsChronic    = 1 -> tells the reviewer this is ongoing treatment, not a new case
-- IsHereditary = 1 -> surfaces on the CHILDREN's claims as family background
-- ConditionCode is ICD-10 so it can be matched against a claim's diagnosis.
--
-- Left empty on purpose. Add only conditions that belong to your real test data.
--
-- INSERT INTO MedicalHistory
--     (user_ID, ConditionCode, ConditionName, IsChronic, IsHereditary, DiagnosedOn, Notes)
-- VALUES
--     (1, 'E11', 'Type 2 diabetes mellitus', 1, 1, '2019-04-12',
--      'Chronic and hereditary. HbA1c monitored every six months.');


-- ----------------------------------------------------------------------------
-- 5. Recurring treatments eligible for automation   ***  OPTIONAL  ***
-- ----------------------------------------------------------------------------
-- A claim matching BenefitCode + ConditionCode, costing no more than MaxAmount,
-- arriving at least IntervalDays after LastApproved, is approved automatically
-- by decision_engine.py without reaching a reviewer.
-- Leave LastApproved NULL so the first matching claim is auto-approved.
--
-- INSERT INTO RecurringTreatments
--     (user_ID, BenefitCode, ConditionCode, Description, IntervalDays, MaxAmount, LastApproved)
-- VALUES
--     (1, 'PRIMARY_CARE', 'E11', 'HbA1c diabetes follow-up test', 180, 400, NULL);


-- ----------------------------------------------------------------------------
-- Verify
-- ----------------------------------------------------------------------------
SELECT 'MemberPolicy'        AS table_name, COUNT(*) AS rows FROM MemberPolicy
UNION ALL SELECT 'FamilyLinks',         COUNT(*) FROM FamilyLinks
UNION ALL SELECT 'DataSharingConsent',  COUNT(*) FROM DataSharingConsent
UNION ALL SELECT 'MedicalHistory',      COUNT(*) FROM MedicalHistory
UNION ALL SELECT 'RecurringTreatments', COUNT(*) FROM RecurringTreatments;