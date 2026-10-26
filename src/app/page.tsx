"use client";

import { useState } from "react";

type Passage = { text: string; word_count: number; ai_probability: number };
type Result = {
  ai_probability: number;
  label: "AI-generated" | "Human-written";
  band: string;
  threshold: number;
  word_count: number;
  passages: Passage[];
};

// Same limits the API enforces (src/api/main.py), checked here so the button can say why it is off.
const MIN_WORDS = 50;
const MAX_WORDS = 5000;
const THRESHOLD_PCT = 55; // decision threshold, same as THRESHOLD in src/api/detector.py
const SERVICE_DOWN = "Can't reach the detector service. Start it from the project root:";
const START_COMMAND = "uvicorn api.main:app --app-dir src --port 8000";

async function errorMessage(res: Response): Promise<string> {
  if (res.status >= 500) return SERVICE_DOWN; // the Next.js proxy answers 5xx when FastAPI is not running
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {}
  return `The detector could not score this text (error ${res.status}).`;
}

function BandRail({ score }: { score: number | null }) {
  return (
    <div className="rail-wrap">
      <div
        className="rail"
        role="img"
        aria-label={
          score === null
            ? `Scale from 0 to 100 percent: likely human up to 20, mixed from 21 to 79, highly likely AI from 80, decision threshold at ${THRESHOLD_PCT}.`
            : `${score} percent on a scale from 0 to 100; decision threshold at ${THRESHOLD_PCT}.`
        }
      >
        <i />
        <i />
        <i />
        <span className="threshold" style={{ left: `${THRESHOLD_PCT}%` }} />
        {score !== null && <span className="needle" style={{ left: `${score}%` }} />}
      </div>
      {/* Numbers sit at their true positions on the rail; band names follow the segments. */}
      <div className="rail-numbers" aria-hidden="true">
        <span style={{ left: "0%" }}>0</span>
        <span style={{ left: "20%" }}>20</span>
        <span style={{ left: `${THRESHOLD_PCT}%` }}>{THRESHOLD_PCT} · threshold</span>
        <span style={{ left: "80%" }}>80</span>
        <span style={{ left: "100%" }}>100</span>
      </div>
      <div className="rail-bands" aria-hidden="true">
        <span>Likely human</span>
        <span>Possible AI assistance / mixed</span>
        <span>Highly likely AI</span>
      </div>
    </div>
  );
}

export default function Home() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const hint =
    words === 0
      ? `Paste ${MIN_WORDS}–${MAX_WORDS.toLocaleString()} words.`
      : words < MIN_WORDS
        ? `${MIN_WORDS - words} more words needed.`
        : words > MAX_WORDS
          ? `Over the ${MAX_WORDS.toLocaleString()}-word limit.`
          : "Ready to check.";
  const canCheck = !loading && words >= MIN_WORDS && words <= MAX_WORDS;

  async function check() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/detect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (res.ok) setResult(await res.json());
      else {
        setResult(null);
        setError(await errorMessage(res));
      }
    } catch {
      setResult(null);
      setError(SERVICE_DOWN);
    } finally {
      setLoading(false);
    }
  }

  function clear() {
    setText("");
    setResult(null);
    setError(null);
  }

  return (
    <>
      <header className="masthead">
        <h1 className="wordmark">
          Penned <b>or</b> Prompted?
        </h1>
        <p className="method">Hybrid detector · spaCy + ELECTRA + XGBoost · UST CICS thesis</p>
      </header>

      <main className="grid">
        <section className="paste" aria-label="Text to check">
          <label htmlFor="essay" className="token">
            Paste an academic text
          </label>
          <textarea
            id="essay"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste an essay, report or abstract in English. Code, equations and citations are set aside before scoring."
            spellCheck={false}
          />
          <div className="paste-foot">
            <span className="token" aria-live="polite">
              {words.toLocaleString()} words · {hint}
            </span>
            <div className="actions">
              <button type="button" className="secondary" onClick={clear} disabled={!text && !result}>
                Clear
              </button>
              <button type="button" className="primary" onClick={check} disabled={!canCheck}>
                {loading ? "Checking…" : "Check text"}
              </button>
            </div>
          </div>
        </section>

        <section className="result" aria-live="polite" aria-busy={loading}>
          {error && (
            <p className="error" role="alert">
              {error}
              {error === SERVICE_DOWN && <code>{START_COMMAND}</code>}
            </p>
          )}

          {result ? (
            <>
              <p className="score">
                {Math.round(result.ai_probability)}
                <span>%</span>
              </p>
              <p className="score-caption">AI-generation probability</p>
              <p className="band">{result.band}</p>
              <BandRail score={result.ai_probability} />
              <p className="token">
                Table 4 bands · {result.ai_probability >= result.threshold * 100 ? "above" : "below"}{" "}
                {result.threshold.toFixed(2)} threshold
              </p>
              <dl className="tokens">
                <div>
                  <dt>Words</dt>
                  <dd>{result.word_count.toLocaleString()}</dd>
                </div>
                <div>
                  <dt>Passages</dt>
                  <dd>{result.passages.length}</dd>
                </div>
                <div>
                  <dt>Threshold</dt>
                  <dd>{result.threshold.toFixed(2)}</dd>
                </div>
              </dl>
              <p className="caveat">
                A probability, not proof. Built for English academic writing that is fully AI-generated (GPT-3.5,
                Claude, Gemini). Nothing you paste is stored.
              </p>

              <h2 className="token">Score by passage</h2>
              <ol className="passages">
                {result.passages.map((p, i) => (
                  <li key={i}>
                    <span className="index">{String(i + 1).padStart(2, "0")}</span>
                    <p className="excerpt">{p.text}</p>
                    <span className="bar" aria-hidden="true">
                      <i style={{ width: `${p.ai_probability}%` }} />
                    </span>
                    <span className="value">{Math.round(p.ai_probability)}%</span>
                  </li>
                ))}
              </ol>
            </>
          ) : (
            !error && (
              <>
                <p className="placeholder">
                  {loading
                    ? "Scoring each passage with the hybrid model…"
                    : "Your result appears here: the probability, where it falls on the study's three bands, and a score for each passage."}
                </p>
                <BandRail score={null} />
                <p className="caveat">
                  A probability, not proof. Built for English academic writing that is fully AI-generated (GPT-3.5,
                  Claude, Gemini). Nothing you paste is stored.
                </p>
              </>
            )
          )}
        </section>
      </main>
    </>
  );
}
