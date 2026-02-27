# Image Reading Data and Reporting

## Visualisation overview

- `visualisation.py` contains reusable helpers to:
  - load CSV tables from `large_data/`
  - build the reader-level summary table used in analysis
  - filter summary outputs by `BSO Code`
  - generate the three matplotlib charts used at the end of the notebook:
    - Elliptical chart (`Discrepant Cancer Rate` vs `Recall Rate`)
    - Quadrant chart (`Cancer Detection Rate` vs `Recall Rate`)
    - Funnel chart (`Cancer Detection Rate` vs `Number of first reads`)
- `streamlit_demo.py` is a lightweight Streamlit UI that imports those functions and displays:
  - 4 tabs (Summary Table + 3 charts)
  - a BSO filter in each tab
  - the same chart logic as the notebook, without duplicating plotting code

Run the app from this directory with:

```bash
poetry run streamlit run streamlit_demo.py
```

The rest of the document describes, in simple pseudocode, how each KPI in `kpis.py` is calculated.

## Data loading

```text
LOAD all CSV files in ./data into dictionary tables
RUN preprocess_kpi_data(tables)
BUILD rd_enriched by joining:
  ReadDecision -> ReadEpisode -> Image -> Appointment -> ScreeningEpisode -> Participant
```

---

## 1) Number of Images read

```text
FOR each reader in Reader table:
  COUNT distinct read_decision_id in rd_enriched for that reader
RETURN per-reader count as read_decision_count
```

---

## 2) Number recalled for assessment

```text
FILTER rd_enriched where reader_decision == "Recall for Assessment"
FOR each reader:
  COUNT distinct read_decision_id
RETURN per-reader count as recalled_for_assessment_count
```

---

## 3) % Recalled for assessment

```text
JOIN read_decision_count with recalled_for_assessment_count by reader_id
FOR each reader:
  recalled_for_assessment_pct =
    (recalled_for_assessment_count / read_decision_count) * 100
  IF denominator is 0 -> set to 0
ROUND to 2 decimals
```

---

## 4) PPV of Recall for Assessment

```text
TAKE recalled episodes per reader from rd_enriched
JOIN to CancerPresence by read_episode_id
FOR each reader:
  numerator = count of recalled episodes where cancer_present == TRUE
  denominator = recalled_for_assessment_count
  ppv_recall_for_assessment_pct = (numerator / denominator) * 100
  IF denominator is 0 -> set to 0
ROUND to 2 decimals
```

---

## 5) Number Cancers Detected

```text
TAKE recalled episodes per reader from rd_enriched
JOIN to CancerPresence by read_episode_id
KEEP rows where cancer_present == TRUE
FOR each reader:
  COUNT distinct read_episode_id
RETURN cancers_detected_count
```

---

## 6) Cancer Detection rate per 1000

```text
JOIN cancers_detected_count with read_decision_count by reader_id
FOR each reader:
  cancer_detection_rate_per_1000 =
    (cancers_detected_count / read_decision_count) * 1000
  IF denominator is 0 -> set to 0
ROUND to 2 decimals
```

---

## 7) Number discrepant cancers

Definition used:
A discrepant cancer for a reader means:

- cancer is present,
- this reader did NOT recall,
- and either another reader OR arbitration did recall.

```text
GET cancer-positive episodes from CancerPresence
GET per-reader decisions from ReadDecision for those episodes
FOR each episode:
  count how many readers recalled
  detect whether arbitration decision includes recall
FOR each reader decision row:
  mark discrepant if:
    reader_recalled == FALSE
    AND (other_reader_recalled == TRUE OR arbitration_recalled == TRUE)
FOR each reader:
  COUNT distinct discrepant read_episode_id
RETURN discrepant_cancers_count
```

---

## 8) Discrepant cancer rate

Reader-aligned rate:

```text
FOR each reader:
  total_cancer_cases_for_reader =
    cancers_detected_count + discrepant_cancers_count
  discrepant_cancer_rate_pct =
    (discrepant_cancers_count / total_cancer_cases_for_reader) * 100
  IF denominator is 0 -> set to 0
ROUND to 2 decimals
```

---

## 9) Number biopsies

```text
TAKE recalled episodes per reader from rd_enriched
JOIN to Biopsies by read_episode_id
FOR each reader:
  COUNT distinct read_episode_id
RETURN biopsies_count
```

---

## 10) Rate of benign biopsy per 1000

```text
TAKE recalled episodes per reader from rd_enriched
JOIN to Biopsies by read_episode_id
KEEP rows where biopsy_result == "benign"
FOR each reader:
  benign_biopsies_count = COUNT distinct read_episode_id
  benign_biopsy_rate_per_1000 =
    (benign_biopsies_count / read_decision_count) * 1000
  IF denominator is 0 -> set to 0
ROUND to 2 decimals
```

---

## 11) Number interval cancers

```text
GET participants where IntervalCancers.interval_cancer_found == TRUE
GET unique (reader_id, participant_id) pairs from rd_enriched
JOIN the two sets on participant_id
FOR each reader:
  COUNT distinct participant_id
RETURN interval_cancers_count
```

---

## 12) Average time to read

```text
FROM ReadEpisode:
  first_duration  = first_reader_ended_at  - first_reader_started_at
  second_duration = second_reader_ended_at - second_reader_started_at
NORMALISE both into rows with columns: reader_id, started_at, ended_at
UNION first and second rows
COMPUTE read_time_minutes = (ended_at - started_at) in minutes
FOR each reader:
  average_read_time_minutes = mean(read_time_minutes)
  read_sessions_count       = count(read_time_minutes)
ROUND average to 2 decimals
```

---

## Notes

- All KPI tables are reader-level outputs.
- Where a denominator could be zero, KPI value is set to 0.
- Distinct counting is used to avoid duplicate episode/participant inflation.
- This pseudocode mirrors the current KPI functions in `projects/synthetic_image_reading_data/kpis.py`.
