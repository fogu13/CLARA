"use client";

import { useState } from "react";
import { updateProblem } from "../../lib/client-api";
import type { ProblemRecord } from "../../lib/types";

type EditorState = {
  status: "idle" | "saving" | "saved" | "error";
  message: string;
};

export function DraftProblemEditor({ problem }: { problem: ProblemRecord }) {
  const [title, setTitle] = useState(problem.title);
  const [statement, setStatement] = useState(problem.statement);
  const [owner, setOwner] = useState(problem.owner);
  const [rootCauseHypothesis, setRootCauseHypothesis] = useState(problem.root_cause_hypothesis);
  const [editorState, setEditorState] = useState<EditorState>({
    status: "idle",
    message: "Draft problem fields can be refined before approval."
  });

  if (!problem.problem_id.startsWith("PRB-DRAFT-")) {
    return null;
  }

  async function saveDraft() {
    setEditorState({ status: "saving", message: "Saving draft problem..." });

    try {
      const updated = await updateProblem(problem.problem_id, {
        title,
        statement,
        owner,
        root_cause_hypothesis: rootCauseHypothesis
      });
      setTitle(updated.title);
      setStatement(updated.statement);
      setOwner(updated.owner);
      setRootCauseHypothesis(updated.root_cause_hypothesis);
      setEditorState({
        status: "saved",
        message: "Draft problem saved. Refreshing queue..."
      });
      window.location.reload();
    } catch (error) {
      setEditorState({
        status: "error",
        message: error instanceof Error ? error.message : "Could not save draft problem."
      });
    }
  }

  return (
    <section className="draft-editor" aria-label="Edit draft problem">
      <h3>Edit Draft Problem</h3>
      <div className="draft-editor-grid">
        <label>
          Title
          <input value={title} onChange={(event) => setTitle(event.target.value)} />
        </label>
        <label>
          Owner
          <input value={owner} onChange={(event) => setOwner(event.target.value)} />
        </label>
      </div>
      <label>
        Statement
        <textarea value={statement} rows={3} onChange={(event) => setStatement(event.target.value)} />
      </label>
      <label>
        Root-cause hypothesis
        <textarea
          value={rootCauseHypothesis}
          rows={3}
          onChange={(event) => setRootCauseHypothesis(event.target.value)}
        />
      </label>
      <div className="draft-editor-actions">
        <button type="button" disabled={editorState.status === "saving"} onClick={saveDraft}>
          Save draft problem
        </button>
        <p className={`draft-editor-message draft-editor-${editorState.status}`}>
          {editorState.message}
        </p>
      </div>
    </section>
  );
}
