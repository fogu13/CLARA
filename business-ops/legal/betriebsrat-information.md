# CLARA — Betriebsrat-Information (Informationsblatt, eine Seite)

_Einseitiges Informationsblatt für den **Betriebsrat des Kunden**. Es beschreibt, welche
beschäftigtenbezogenen Daten CLARA verarbeitet, was das System **nicht** tut, und wie der
**Betriebsrat-Modus** eine Verhaltens- und Leistungskontrolle technisch ausschließt. Der Kunde
kann dieses Blatt unverändert in sein Mitbestimmungsverfahren nach **§ 87 Abs. 1 Nr. 6 BetrVG**
mitnehmen — mitbestimmungspflichtig ist jede technische Einrichtung, die zur Überwachung von
Verhalten oder Leistung **objektiv geeignet** ist; auf eine Überwachungs*absicht* kommt es nach
der Rechtsprechung des BAG nicht an._

> **ENTWURF — vor Verwendung durch einen Fachanwalt (Arbeitsrecht/IT-Recht) prüfen lassen.**
> Founder-Entwurf, keine Rechtsberatung. Im selben Review-Termin prüfen lassen wie AVV/TOMs
> (siehe [README.md](README.md)); zusätzlich die geplante **eine Stunde mit einer
> Fachanwältin/einem Fachanwalt für IT-/Arbeitsrecht** zur Reichweite von § 87 Abs. 1 Nr. 6 BetrVG
> nutzen, bevor das Blatt in Vertriebsunterlagen wandert. Alle `{{PLATZHALTER}}` ausfüllen.

---

## 1. Was CLARA ist — und wozu es nicht dient

CLARA ({{LEGAL_ENTITY_NAME}}, {{ADDRESS}}) ist ein SaaS-Werkzeug zur **Bündelung und Priorisierung
von Kundenfeedback** (Tickets, Bewertungen, Store-Feedback). Beschäftigte des Kunden nutzen es, um
Kundenprobleme zu sichten, Maßnahmen freizugeben und deren Wirkung zu messen. **Zweck ist die
Analyse von Kundenfeedback — nicht die Bewertung von Beschäftigten.** Es werden keine
Arbeitszeiten erfasst, keine Produktivitätsprofile gebildet und keine Beschäftigten-Rankings
erzeugt.

## 2. Welche beschäftigtenbezogenen Daten anfallen

| Datenkategorie | Beispiel | Zweck | Speicherdauer |
|---|---|---|---|
| Anmeldedaten (Konto) | Name, dienstliche E-Mail, Rolle | Zugriffskontrolle (RBAC) | Vertragslaufzeit |
| Freigabe-Protokoll | wer hat eine Maßnahme wann freigegeben/abgelehnt (+ optionale Notiz) | Nachvollziehbarkeit, Audit-Pflichten (EU AI Act Art. 14 – menschliche Aufsicht) | {{AUFBEWAHRUNG_AUDIT, z. B. Vertragslaufzeit + gesetzl. Fristen}} |
| Zuständigkeiten | verantwortliche Person je Maßnahme („Owner") | Arbeitsorganisation | Vertragslaufzeit |
| Lern-/Abschlussvermerke | pseudonymisierte Bearbeiter-Kennung (`user-xxxxxxxx`) | Qualitätssicherung | 730 Tage, danach automatische Löschung |

Grundlage der Verarbeitung im Auftrag des Kunden ist der AVV ([avv-dpa.md](avv-dpa.md));
technische Schutzmaßnahmen sind in den TOMs ([toms.md](toms.md)) beschrieben. Alle Daten
verbleiben in der EU.

## 3. Objektive Überwachungseignung — und die technische Antwort darauf

Freigabe-Zeitstempel und Zuständigkeitslisten sind — wie in jedem Ticketsystem — **objektiv
geeignet**, Rückschlüsse auf einzelne Beschäftigte zuzulassen (z. B. Freigabedauer je Person).
Deshalb bringt CLARA einen **Betriebsrat-Modus** (`works_council_mode`, je Arbeitsbereich
zuschaltbar) mit:

1. **Nur-aggregierte Beschäftigten-Sichten.** Kennzahlen, die je Person ableitbar wären
   (Freigabedauer, Maßnahmen je Person, Ablehnungsquoten), werden ausschließlich als
   Arbeitsbereich-Aggregate angezeigt; Gruppen mit **weniger als 5 Personen werden unterdrückt**
   (k-Anonymität).
2. **Rollen-redigierte Audit-Exporte.** In Standard-Exporten werden Personenkennungen durch
   **Rollenbezeichnungen** ersetzt (z. B. „Freigebende/r", „Owner"). Die Audit-*Kette* bleibt
   für Compliance-Zwecke vollständig; die *Person* ist in Routine-Exporten nicht rückverfolgbar.
3. **Benannter Vollzugriff.** Nur die in der Betriebsvereinbarung **namentlich zu benennende
   Admin-Rolle** (z. B. Datenschutzbeauftragte/r) kann Exporte mit Klarnamen erzeugen — für
   gesetzliche Nachweispflichten.
4. **Transparenz im Produkt.** Betroffene Ansichten tragen einen sichtbaren Hinweis
   („aggregiert im Betriebsrat-Modus"); der Modus wird in den Arbeitsbereich-Einstellungen
   dokumentiert umgeschaltet.

## 4. Empfohlene Regelungspunkte für die Betriebsvereinbarung

- Betriebsrat-Modus **dauerhaft aktiviert** für Arbeitsbereiche mit Beschäftigtendaten;
- Benennung der zugriffsberechtigten Admin-Rolle (Klarnamen-Exporte) und der Anlässe;
- Ausschluss der Nutzung von CLARA-Daten für Leistungs-/Verhaltensbewertung einzelner
  Beschäftigter;
- Speicher- und Löschfristen gem. Abschnitt 2; Beteiligung des Betriebsrats bei
  wesentlichen Funktionsänderungen.

**Kontakt:** {{NAME}}, {{E-MAIL_SECURITY_KONTAKT}} — wir stellen dem Betriebsrat auf Wunsch eine
Live-Demonstration des Betriebsrat-Modus und die vollständige Dokumentation (AVV, TOMs,
Subprozessorenliste) zur Verfügung.

---

_Stand: {{DATUM}} · Produktfunktion `works_council_mode` ausgeliefert mit Workstream W1
(Juli 2026, siehe `../../docs/archive/plan-strategy-implementation-2026-07.md`)._
