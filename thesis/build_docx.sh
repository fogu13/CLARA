#!/usr/bin/env bash
# Rebuild build/thesis_combined.md + build/thesis.docx from the current sources.
# Assembly replicates the previous build's structure: chapters -> References ->
# Appendix A (study instruments) -> B/C/D (manuscript appendices) -> E (schema).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
OUT=build/thesis_combined.md
: > "$OUT"

for f in manuscript/00_front_matter.md manuscript/01_introduction.md \
         manuscript/02_literature_review.md manuscript/03_methodology.md \
         manuscript/04_artifact.md manuscript/05_evaluation_results.md \
         manuscript/06_discussion.md manuscript/07_conclusion.md \
         manuscript/references.md; do
  cat "$f" >> "$OUT"; printf '\n\n---\n\n' >> "$OUT"
done

printf '# Appendix A: Study Instruments\n\n' >> "$OUT"
for f in instruments/consent_and_recruitment.md instruments/interview_guide.md \
         instruments/survey.md instruments/sus_questionnaire.md \
         instruments/tam_items.md instruments/codebook_template.md; do
  cat "$f" >> "$OUT"; printf '\n\n---\n\n' >> "$OUT"
done

printf '# Appendix B: EU AI Act / GDPR Mapping\n\n' >> "$OUT"
tail -n +2 manuscript/appendices/B_eu_ai_act_gdpr_mapping.md >> "$OUT"
printf '\n\n---\n\n# Appendix C: Data Protection Impact Assessment\n\n' >> "$OUT"
tail -n +2 manuscript/appendices/C_dpia.md >> "$OUT"
printf '\n\n---\n\n# Appendix D: Traceability Matrix\n\n' >> "$OUT"
tail -n +2 manuscript/appendices/D_traceability_matrix.md >> "$OUT"

if [ -f diagrams/schema.sql ]; then
  printf '\n\n---\n\n# Appendix E: Data Model DDL (schema.sql)\n\n```sql\n' >> "$OUT"
  cat diagrams/schema.sql >> "$OUT"
  printf '\n```\n' >> "$OUT"
fi

# Images in chapters use ../diagrams/... relative to manuscript/; the combined
# file lives in build/, for which ../diagrams/ also resolves correctly.
cd build
pandoc thesis_combined.md \
  --from markdown+tex_math_dollars \
  --toc --toc-depth=2 \
  --metadata title="Closing the Loop, Building the Memory" \
  -o thesis.docx
echo "built: $(du -h thesis.docx | cut -f1) thesis.docx"
