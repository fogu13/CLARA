# Betriebsrat-Paket: Feature-/Kontroll-Matrix

Technischer Anhang: welche Einstellung was bewirkt, wo sie erzwungen wird und
wie sie nachgewiesen ist. Alle Angaben sind im Quellcode überprüfbar. Die
Betriebsvereinbarung kann auf diese Matrix verweisen („Konfiguration gemäß
Anlage").

| Kontrolle | Einstellung (wer darf ändern) | Wirkung | Erzwungen in | Nachweis |
|---|---|---|---|---|
| Betriebsrat-Modus | `works_council_mode` (nur Admin) | Rollen-Labels statt Personen in allen Nicht-Admin-Antworten; Evidenz-Pakete an der Quelle redigiert | `services/works_council.py` (Middleware, fail-closed) | Walker-Test über alle GET-Endpunkte, jede CI |
| Vier-Augen-Freigabe | `four_eyes_approval` (nur Admin) | Folgenreiche Maßnahmen brauchen zwei verschiedene Freigebende; Selbstbestätigung wird abgelehnt | `services/workflow.py` (`resolve_approval_state`) | Tests beide Speicher-Implementierungen |
| Freigabe-Identität | nicht abschaltbar | Freigebende:r = verifiziertes Login (Pseudonym), nie aus dem Request-Body | `routers/problems.py` (JWT-Bindung) | End-to-End-Test mit echtem JWT |
| KI-Transparenz (Art. 50) | `ai_disclosure_template` (nur Admin) | Nicht menschlich geprüfte Ausgaben tragen automatisch den KI-Hinweis | `services/action_push.py` | Art.-50-Tests |
| KI-Kompetenz (Art. 4) | Workspace-Attestierung | Nur „Paket ausgehändigt" auf Workspace-Ebene; KEIN Abschluss-Tracking pro Person | `WorkspaceSettings.ai_literacy_pack_delivered_at` | Modellkommentar + Test |
| Audit-Export | Admin-Rolle | Vollexport für die designierte Stelle; Nicht-Admin-Exporte rollenredigiert | `routers/governance.py` | Walker-Test (Exportpfad) |
| Datenlöschung (Art. 17) | Admin-Rolle | Produkt-Endpunkt, kein Ticketprozess | `DELETE /customers/{id}/data` | Test |
| Aufbewahrung Learnings | Server-Konstante (730 Tage) | Automatischer Verfall gespeicherter Learning-Einträge | `domain/models.py` (`retention_expires_at`) | Test |
| Geheimnis-Verschlüsselung | `CLARA_CONFIG_SECRET_KEY` (Server-Env) | Konnektor-Zugangsdaten ruhen verschlüsselt (Fernet) | `connectors/config_store.py` | Test (Ciphertext enthält Klartext nicht) |

**Bewusst nicht vorhanden** (kein Feature, keine „versteckte" Option):
Pro-Person-Auswertungen von Freigabezeiten, Override-Quoten oder
Bearbeitungsleistung; individuelle Schulungs-Abschlussverfolgung;
Mitarbeiter-Ranking jeder Art.
