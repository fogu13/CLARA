# Technische Erklärung: Keine individuelle Leistungs- oder Verhaltenskontrolle

**Technischer Anhang zum Betriebsrat-Paket.** Dieses Dokument enthält
ausschließlich technische Tatsachenbehauptungen, die im Quellcode und in
automatisierten Tests überprüfbar sind. Es ist keine Rechtsberatung; die
Betriebsvereinbarungs-Vorlage folgt nach anwaltlicher Prüfung.

## Zusammenfassung

Bei aktiviertem **Betriebsrat-Modus** (`works_council_mode`, nur durch
Admins änderbar) kann aus keiner CLARA-Ansicht unterhalb der Admin-Rolle eine
personenbezogene Leistungs- oder Verhaltenskennzahl über Beschäftigte
abgeleitet werden.

## Was der Modus technisch erzwingt

1. **Personenfähige Felder werden serverseitig durch Rollenbezeichnungen
   ersetzt** — in JEDER JSON-Antwort unterhalb der Admin-Rolle, an einer
   einzigen Middleware-Sperrstelle (fail-closed: schlägt die Redaktion fehl,
   wird die Antwort nicht ausgeliefert). Ersetzte Felder:
   `reviewer`/`reviewed_by` → „approver", `actor` → „editor",
   `owner`/`assignee`/`responsible_owner` → „owner".
   *(Quelle: `apps/api/app/services/works_council.py`, REDACTED_FIELDS +
   WorksCouncilRedactionMiddleware.)*
2. **Listen personenfähiger Werte kollabieren auf EIN Rollenlabel**, damit
   auch die Anzahl unterscheidbarer Personen nicht ablesbar ist.
3. **Evidenz-Pakete** (der Audit-Export je Problem) werden an der Quelle
   redigiert — auch der HTML-/PDF-Weg, der an der JSON-Middleware vorbeiführt.
4. **Kleingruppen-Unterdrückung** (k = 5) steht als geprüfte Bibliotheksfunktion
   bereit (`k_suppress`): sollte je eine personenbezogene Aggregatansicht
   entstehen, werden Gruppen unter fünf Personen vollständig unterdrückt.
   Derzeit existiert bewusst KEINE serverseitige Pro-Person-Aggregation.
5. **Keine Erfassung individueller Schulungs-Abschlüsse**: die
   KI-Kompetenz-Attestierung (Art. 4) ist absichtlich nur auf Workspace-Ebene
   („Paket ausgehändigt") implementiert — Abschluss-Tracking pro Person wäre
   selbst ein Überwachungsmerkmal und existiert nicht.
6. **Freigabe-Identitäten sind Pseudonyme** (`user-<8 Hex>`), abgeleitet aus
   dem verifizierten Login — keine Klarnamen in Audit-Einträgen unterhalb der
   Admin-Rolle.

## Kontinuierlicher Nachweis

Ein automatisierter Test („Works-Council-Walker",
`apps/api/app/tests/test_works_council_walker.py`) ruft **jeden**
GET-Endpunkt der API mit einer Nicht-Admin-Kennung auf und schlägt fehl,
sobald irgendeine Antwort ein personenfähiges Feld oder einen der eingesäten
Personen-Identifikatoren enthält. Der Test läuft in jeder CI-Ausführung; eine
Regression kann nicht unbemerkt ausgeliefert werden.

## Grenzen (vollständige Transparenz)

- Die designierte **Admin-Rolle** sieht weiterhin vollständige Identitäten —
  die Betriebsvereinbarung benennt üblicherweise, wer diese Rolle innehat.
- Ein Protokoll der Admin-Zugriffe auf Klaridentitäten existiert noch nicht
  (geplant; im Design-Dokument vermerkt).
- Rohtexte von Kundenfeedback können Namen von Beschäftigten enthalten, wenn
  Kund:innen sie nennen; CLARA erzeugt daraus keine Kennzahlen.
