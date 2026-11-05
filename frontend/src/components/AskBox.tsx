import { CircleAlert, FileText, Send, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { AskResponse, DocumentRecord } from "../api";
import { api, getApiError } from "../api";

export function AskBox({ documents }: { documents: DocumentRecord[] }) {
  const [question, setQuestion] = useState("");
  const [scope, setScope] = useState("");
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const answerRef = useRef<HTMLElement>(null);
  async function ask(event?: React.FormEvent) {
    event?.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError("");
    try {
      setAnswer(
        await api.ask(question.trim(), scope ? Number(scope) : undefined),
      );
    } catch (err) {
      setError(getApiError(err, "Could not answer from your documents."));
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    if (answer) {
      answerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [answer]);
  const ready = documents.filter((document) => document.status === "completed");
  return (
    <section>
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[.15em] text-[#e88d35]">
            ASK YOUR DOCUMENTS
          </p>
          <h2 className="mt-2 font-serif text-3xl font-medium tracking-tight text-[#17233b]">
            What would you like to know?
          </h2>
        </div>
        <span className="hidden items-center gap-1.5 rounded-full bg-teal-50 px-3 py-1.5 text-[10px] font-semibold text-teal-700 sm:flex">
          <Sparkles size={14} />
          Grounded answers
        </span>
      </div>
      <form
        onSubmit={(event) => void ask(event)}
        className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
      >
        <div className="mb-3 flex items-center justify-between text-xs text-slate-500">
          <span>Question</span>
          <label className="flex items-center gap-2">
            Search in
            <select
              value={scope}
              onChange={(event) => setScope(event.target.value)}
              className="max-w-44 border-0 bg-transparent text-xs font-semibold text-[#17233b] outline-none"
            >
              <option value="">All ready documents</option>
              {ready.map((document) => (
                <option value={document.id} key={document.id}>
                  {document.filename}
                </option>
              ))}
            </select>
          </label>
        </div>
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="e.g. What documents are required for a domicile certificate?"
          rows={3}
          className="w-full resize-none border-0 bg-transparent text-base leading-7 text-[#17233b] outline-none placeholder:text-slate-300"
        />
        <div className="flex items-center justify-between border-t border-slate-100 pt-3">
          <span className="text-[10px] text-slate-400">
            Find answers across your verified sources
          </span>
          <button
            disabled={busy || !question.trim()}
            className="flex items-center gap-2 rounded-lg bg-[#e88d35] px-4 py-2.5 text-xs font-bold text-white disabled:opacity-50"
          >
            {busy ? "Reading sources…" : "Ask gujdoc"}
            <Send size={14} />
          </button>
        </div>
      </form>
      {error && (
        <p className="mt-4 flex items-center gap-2 text-xs text-red-600">
          <CircleAlert size={14} />
          {error}
        </p>
      )}
      {answer && (
        <article
          ref={answerRef}
          className="mt-5 scroll-mt-24 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
        >
          <div className="flex items-center gap-2 border-b border-slate-100 px-5 pb-3 pt-5 text-xs font-bold text-teal-700">
            <Sparkles size={15} />
            Gujdoc answer
          </div>
          <div className="answer-content px-5 py-5 text-[15px] leading-7 text-slate-600">
            <AnswerContent text={answer.answer} />
          </div>
          {answer.sources.length > 0 && (
            <div className="border-t border-slate-100 bg-slate-50/60 px-5 py-4">
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Sources used
              </p>
              {answer.sources.map((source) => (
                <div
                  className="flex items-center gap-2 py-2"
                  key={source.chunk_id}
                >
                  <span className="grid h-5 w-5 place-items-center rounded bg-orange-50 text-[10px] font-bold text-[#d37d2c]">
                    {source.source_number}
                  </span>
                  <div>
                    <strong className="block text-xs text-slate-600">
                      {source.filename}
                    </strong>
                    <span className="text-[10px] text-slate-400">
                      Page {source.page_number}
                    </span>
                  </div>
                  <FileText size={14} className="ml-auto text-slate-300" />
                </div>
              ))}
            </div>
          )}
        </article>
      )}
    </section>
  );
}

function AnswerContent({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/);
  return (
    <>
      {blocks.map((block, index) => {
        const lines = block.split("\n").filter((line) => line.trim());
        if (!lines.length) return null;
        if (lines.every((line) => /^[-*]\s+/.test(line))) {
          return (
            <ul className="mb-4 list-disc space-y-1 pl-5 last:mb-0" key={index}>
              {lines.map((line) => (
                <li key={line}>{formatInline(line.replace(/^[-*]\s+/, ""))}</li>
              ))}
            </ul>
          );
        }
        if (lines.every((line) => /^\d+[.)]\s+/.test(line))) {
          return (
            <ol className="mb-4 list-decimal space-y-1 pl-5 last:mb-0" key={index}>
              {lines.map((line) => (
                <li key={line}>{formatInline(line.replace(/^\d+[.)]\s+/, ""))}</li>
              ))}
            </ol>
          );
        }
        return (
          <div className="mb-4 last:mb-0" key={index}>
            {lines.map((line) =>
              /^#{1,3}\s+/.test(line) ? (
                <h3 className="mb-2 mt-1 font-serif text-lg font-semibold text-[#17233b]" key={line}>
                  {formatInline(line.replace(/^#{1,3}\s+/, ""))}
                </h3>
              ) : (
                <p className="mb-1 last:mb-0" key={line}>{formatInline(line)}</p>
              ),
            )}
          </div>
        );
      })}
    </>
  );
}

function formatInline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[Source\s+\d+\])/gi);
  return parts.map((part, index) => {
    if (/^\*\*[^*]+\*\*$/.test(part)) {
      return <strong className="font-bold text-[#17233b]" key={index}>{part.slice(2, -2)}</strong>;
    }
    if (/^`[^`]+`$/.test(part)) {
      return <code className="rounded bg-slate-100 px-1.5 py-0.5 text-[13px] text-[#17233b]" key={index}>{part.slice(1, -1)}</code>;
    }
    if (/^\[Source\s+\d+\]$/i.test(part)) {
      return <span className="ml-1 rounded bg-orange-50 px-1.5 py-0.5 text-xs font-bold text-[#d37d2c]" key={index}>{part}</span>;
    }
    return part;
  });
}
