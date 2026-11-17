import { useRef, useState } from 'react';
import { useLoanStore } from '../../../store/useLoanStore';
import { FileUp, CheckCircle2, ScanFace, ArrowRight, ShieldCheck, Loader2, AlertCircle } from 'lucide-react';
import { api } from '../../../lib/api';

interface KycWidgetProps {
  onNext?: () => void;
}

type UploadState = 'idle' | 'uploading' | 'done' | 'error';

export default function KycWidget({ onNext }: KycWidgetProps) {
  const { sessionId, setState } = useLoanStore();
  const [aadhaarState, setAadhaarState] = useState<UploadState>('idle');
  const [panState, setPanState] = useState<UploadState>('idle');
  const [isFetchingDigiLocker, setIsFetchingDigiLocker] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const aadhaarRef = useRef<HTMLInputElement>(null);
  const panRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (doc: 'AADHAAR' | 'PAN', file: File) => {
    setUploadError(null);
    const setter = doc === 'AADHAAR' ? setAadhaarState : setPanState;
    setter('uploading');

    if (sessionId) {
      const res = await api.uploadDocument(sessionId, doc, file);
      if (res.success) {
        setter('done');
      } else {
        setter('error');
        setUploadError(res.error || 'Upload failed. Please try again.');
      }
    } else {
      // No session yet — accept locally and let the next step create one
      await new Promise((r) => setTimeout(r, 800));
      setter('done');
    }
  };

  const handleDigiLockerFetch = async () => {
    setIsFetchingDigiLocker(true);
    setUploadError(null);
    try {
      if (sessionId) {
        const res = await api.fetchDigiLocker(sessionId);
        if (!res.success) throw new Error(res.error || 'DigiLocker fetch failed');
      } else {
        await new Promise((r) => setTimeout(r, 800));
      }
      setAadhaarState('done');
      setPanState('done');
    } catch (e: any) {
      setUploadError(e.message || 'DigiLocker fetch failed. Please upload manually.');
    } finally {
      setIsFetchingDigiLocker(false);
    }
  };

  const handleProceed = () => {
    setState('DECISION_READY');
    if (onNext) onNext();
  };

  const isVerified = aadhaarState === 'done' || panState === 'done';

  const docRow = (
    label: string,
    sub: string,
    state: UploadState,
    inputRef: React.RefObject<HTMLInputElement>,
    docType: 'AADHAAR' | 'PAN',
  ) => (
    <div
      onClick={() => state === 'idle' && inputRef.current?.click()}
      className={`p-4 rounded-xl border flex items-center justify-between transition-all ${
        state === 'done'
          ? 'bg-emerald-500/10 border-emerald-500/30 cursor-default'
          : state === 'error'
          ? 'bg-red-500/10 border-red-500/30 cursor-pointer'
          : 'bg-[#0A0A0A] border-white/10 border-dashed hover:border-white/30 cursor-pointer'
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*,application/pdf"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFileSelect(docType, file);
          e.target.value = '';
        }}
      />
      <div>
        <h4 className="font-medium text-white mb-1">{label}</h4>
        <p className="text-xs text-white/40 uppercase tracking-widest font-medium">{sub}</p>
      </div>
      {state === 'done' && <CheckCircle2 className="w-6 h-6 text-emerald-500" />}
      {state === 'uploading' && <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />}
      {state === 'error' && <AlertCircle className="w-5 h-5 text-red-400" />}
      {state === 'idle' && <FileUp className="w-5 h-5 text-white/50" />}
    </div>
  );

  return (
    <div className="bg-[#111] border border-white/10 rounded-2xl p-6 w-full max-w-xl shadow-xl relative overflow-hidden group">
      <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/5 rounded-full blur-3xl group-hover:bg-amber-500/10 transition-colors" />

      <div className="flex justify-between items-center mb-6 relative z-10">
        <div>
          <h3 className="text-xl font-display font-medium text-white tracking-tight flex items-center gap-2">
            <ScanFace className="w-5 h-5 text-amber-500" />
            Vision AI Identity Verification
          </h3>
          <p className="text-xs text-white/40 mt-1">Upload Aadhaar or PAN — or use 1-Click DigiLocker</p>
        </div>

        <button
          onClick={handleDigiLockerFetch}
          disabled={isFetchingDigiLocker || isVerified}
          className="px-3.5 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-xl text-xs font-medium transition-all flex items-center gap-1.5 disabled:opacity-50 shrink-0"
        >
          {isFetchingDigiLocker ? (
            <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Fetching DigiLocker...</>
          ) : (
            <><ShieldCheck className="w-3.5 h-3.5" /> 1-Click DigiLocker</>
          )}
        </button>
      </div>

      {uploadError && (
        <div className="mb-4 px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-400 flex items-center gap-2 relative z-10">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {uploadError}
        </div>
      )}

      <div className="space-y-4 relative z-10">
        {docRow('Aadhaar XML / Image', 'UIDAI 12-Digit Identity', aadhaarState, aadhaarRef, 'AADHAAR')}
        {docRow('PAN Card', 'Income Tax Dept Record', panState, panRef, 'PAN')}

        <button
          onClick={handleProceed}
          disabled={!isVerified}
          className="w-full mt-6 h-12 bg-white text-black rounded-lg font-medium shadow-lg shadow-white/10 hover:shadow-white/20 hover:scale-[1.02] transition-all disabled:opacity-30 flex items-center justify-center gap-2"
        >
          <span className="flex items-center gap-2 font-semibold">
            Initiate Underwriting Decision Engine
            <ArrowRight className="w-4 h-4" />
          </span>
        </button>
      </div>
    </div>
  );
}
