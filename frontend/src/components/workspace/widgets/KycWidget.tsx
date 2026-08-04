import { useState } from 'react';
import { useLoanStore } from '../../../store/useLoanStore';
import { FileUp, CheckCircle2, ScanFace, ArrowRight, ShieldCheck, Loader2 } from 'lucide-react';
import { api } from '../../../lib/api';

interface KycWidgetProps {
  onNext?: () => void;
}

export default function KycWidget({ onNext }: KycWidgetProps) {
  const { sessionId, setState } = useLoanStore();
  const [aadhaarVerified, setAadhaarVerified] = useState(false);
  const [panVerified, setPanVerified] = useState(false);
  const [isFetchingDigiLocker, setIsFetchingDigiLocker] = useState(false);

  const handleUpload = (doc: 'AADHAAR' | 'PAN') => {
    if (doc === 'AADHAAR') setAadhaarVerified(true);
    if (doc === 'PAN') setPanVerified(true);
  };

  const handleDigiLockerFetch = async () => {
    setIsFetchingDigiLocker(true);
    try {
      if (sessionId) {
        await api.fetchDigiLocker(sessionId);
      } else {
        await new Promise((r) => setTimeout(r, 600));
      }
      setAadhaarVerified(true);
      setPanVerified(true);
    } catch (e) {
      console.error(e);
    } finally {
      setIsFetchingDigiLocker(false);
    }
  };

  const handleProceed = () => {
    setState('DECISION_READY');
    if (onNext) onNext();
  };

  // Either Aadhaar OR PAN is sufficient for identity verification
  const isVerified = aadhaarVerified || panVerified;

  return (
    <div className="bg-[#111] border border-white/10 rounded-2xl p-6 w-full max-w-xl shadow-xl relative overflow-hidden group">
      <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/5 rounded-full blur-3xl group-hover:bg-amber-500/10 transition-colors" />
      
      <div className="flex justify-between items-center mb-6 relative z-10">
        <div>
          <h3 className="text-xl font-display font-medium text-white tracking-tight flex items-center gap-2">
            <ScanFace className="w-5 h-5 text-amber-500" />
            Vision AI Identity Verification
          </h3>
          <p className="text-xs text-white/40 mt-1">Select either Aadhaar OR PAN to proceed</p>
        </div>

        <button
          onClick={handleDigiLockerFetch}
          disabled={isFetchingDigiLocker || isVerified}
          className="px-3.5 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-xl text-xs font-medium transition-all flex items-center gap-1.5 disabled:opacity-50 shrink-0"
        >
          {isFetchingDigiLocker ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" /> Fetching DigiLocker...
            </>
          ) : (
            <>
              <ShieldCheck className="w-3.5 h-3.5" /> 1-Click DigiLocker Auto-Fetch
            </>
          )}
        </button>
      </div>

      <div className="space-y-4 relative z-10">
        <div 
          onClick={() => !aadhaarVerified && handleUpload('AADHAAR')}
          className={`p-4 rounded-xl border flex items-center justify-between transition-all ${
            aadhaarVerified 
              ? 'bg-emerald-500/10 border-emerald-500/30 cursor-default' 
              : 'bg-[#0A0A0A] border-white/10 border-dashed hover:border-white/30 cursor-pointer'
          }`}
        >
          <div>
            <h4 className="font-medium text-white mb-1">Aadhaar XML Record</h4>
            <p className="text-xs text-white/40 uppercase tracking-widest font-medium">UIDAI 12-Digit Identity</p>
          </div>
          {aadhaarVerified ? (
            <CheckCircle2 className="w-6 h-6 text-emerald-500" />
          ) : (
            <FileUp className="w-5 h-5 text-white/50" />
          )}
        </div>

        <div 
          onClick={() => !panVerified && handleUpload('PAN')}
          className={`p-4 rounded-xl border flex items-center justify-between transition-all ${
            panVerified 
              ? 'bg-emerald-500/10 border-emerald-500/30 cursor-default' 
              : 'bg-[#0A0A0A] border-white/10 border-dashed hover:border-white/30 cursor-pointer'
          }`}
        >
          <div>
            <h4 className="font-medium text-white mb-1">PAN Card Record</h4>
            <p className="text-xs text-white/40 uppercase tracking-widest font-medium">Income Tax Dept Record</p>
          </div>
          {panVerified ? (
            <CheckCircle2 className="w-6 h-6 text-emerald-500" />
          ) : (
            <FileUp className="w-5 h-5 text-white/50" />
          )}
        </div>

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
