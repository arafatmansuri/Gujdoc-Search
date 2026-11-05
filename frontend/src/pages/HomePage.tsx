import { RefreshCw } from "lucide-react";
import { useEffect } from "react";
import { AskBox } from "../components/AskBox";
import { DocumentList } from "../components/DocumentList";
import { ProcessingSummary } from "../components/ProcessingSummary";
import { fetchDocuments, invalidateDocuments, useAppDispatch, useAppSelector } from "../store";

export function HomePage() {
  const dispatch = useAppDispatch();
  const { items: documents, error, invalidated } = useAppSelector((state) => state.documents);
  useEffect(() => {
    void dispatch(fetchDocuments());
  }, [dispatch, invalidated]);
  const refresh = () => {
    dispatch(invalidateDocuments());
    void dispatch(fetchDocuments());
  };
  return (
    <div className="space-y-10">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[.15em] text-[#e88d35]">
            YOUR LIBRARY
          </p>
          <h1 className="mt-2 font-serif text-4xl font-medium tracking-tight text-[#17233b]">
            Your documents
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Keep your sources close. Ask when you are ready.
          </p>
        </div>
        <button
          onClick={refresh}
          className="flex items-center gap-2 text-xs text-slate-400 hover:text-[#e88d35]"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>
      {error && <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">{error}</p>}
      <ProcessingSummary />
      <DocumentList documents={documents} />
      <AskBox documents={documents} />
    </div>
  );
}
