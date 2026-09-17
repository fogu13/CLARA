# Follow-up opt-in form (separate from the survey; working material, not bound into the thesis)

A separate form, hosted apart from the supplementary survey (`thesis/instruments/survey.md`) and linked only from the survey's thank-you page, so that a contact detail can never be joined to a set of survey answers. Separate form; not yet used, because the practitioner study had not run at the time of writing (§5B.1).

## Design rules

- The survey and this form live in two separate form objects with separate exports; neither carries an identifier of the other, no timestamp is used to join them, and the survey's `?src=` channel tag is not carried over.
- The only required field is a contact address. Role and company size are asked again here (optional), because they cannot be read across from the survey.
- Entries are stored apart from survey data, used solely to invite interviews under the consent form of `thesis/instruments/consent_and_recruitment.md`, and deleted after recruitment closes.
- Respondents are research contacts, never prospects: Part A of `thesis/instruments/consent_and_recruitment.md` (research-versus-sales separation) applies.

## The form (copy-paste ready)

**Intro (shown first):**
> Thank you for taking the survey. If you'd be open to a 25–30-minute follow-up conversation about how your team acts on customer feedback (for an MSc thesis, Responsible AI, OPIT), leave a way to reach you below. This form is separate from the survey and cannot be linked to your answers there. Your contact detail is used only to invite you to an interview, is stored apart from the survey data, and is deleted once recruitment closes. No sales follow-up, ever. Lawful basis: consent.
> ☐ I consent to being contacted about a research interview on this basis.

- **F1. How can I reach you?** (email or LinkedIn profile) ____________________
- **F2. (Optional) Your role?** ☐ Marketing ☐ Product ☐ Customer Experience / Support ☐ Founder / GM ☐ Other: ___
- **F3. (Optional) Company size?** ☐ 1–9 ☐ 10–50 ☐ 51–200 ☐ 201–500 ☐ 500+
- **F4. (Optional) Anything I should know before getting in touch?** ____________________

**Thank-you page:** "Thanks. I'll be in touch within two weeks if a slot is available; if not, I'll let you know and delete your details."
