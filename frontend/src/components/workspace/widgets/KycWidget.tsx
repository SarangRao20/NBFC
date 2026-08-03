import { useState } from 'react';
import { useLoanStore } from '../../../store/useLoanStore';
import { FileUp, CheckCircle2, ScanFace, ArrowRight } from 'lucide-react';

interface KycWidgetProps {
  onNext?: () => void;
}

export default function KycWidget({ onNext }: KycWidgetProps) {
  const { setState } = useLoanStore();
  const [aadhaarVerified, setAadhaarVerified] = useState(false);
  const [panVerified, setPanVerified] = useState(false);

  const handleUpload = (doc: 'AADHAAR' | 'PAN') => {
    // Instant bypass for testing as requested
    if (doc === 'AADHAAR') setAadhaarVerified(true);
    if (doc === 'PAN') setPanVerified(true);
  };

  const handleProceed = () => {
    setState('DECISION_READY');
    if (onNext) onNext();
  };

  const allVerified = aadhaarVerified && panVerified;

  return (
    <div className="bg-[#111] border border-white/10 rounded-2xl p-6 w-full max-w-xl shadow-xl relative overflow-hidden group">
      <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/5 rounded-full blur-3xl group-hover:bg-amber-500/10 transition-colors" />
      
      <h3 className="text-xl font-display font-medium text-white mb-6 tracking-tight relative z-10 flex items-center gap-2">
        <ScanFace className="w-5 h-5 text-amber-500" />
        Vision AI KYC
      </h3>
      
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
            <h4 className="font-medium text-white mb-1">Aadhaar XML</h4>
            <p className="text-xs text-white/40 uppercase tracking-widest font-medium">Primary Identity</p>
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
            <h4 className="font-medium text-white mb-1">PAN Card</h4>
            <p className="text-xs text-white/40 uppercase tracking-widest font-medium">Financial Identity</p>
          </div>
          {panVerified ? (
            <CheckCircle2 className="w-6 h-6 text-emerald-500" />
          ) : (
            <FileUp className="w-5 h-5 text-white/50" />
          )}
        </div>

        <button 
          onClick={handleProceed}
          disabled={!allVerified}
          className="w-full mt-6 h-12 bg-white text-black rounded-lg font-medium shadow-lg shadow-white/10 hover:shadow-white/20 hover:scale-[1.02] transition-all disabled:opacity-30 flex items-center justify-center gap-2"
        >
          <span className="flex items-center gap-2">
            Initiate Underwriting
            <ArrowRight className="w-4 h-4" />
          </span>
        </button>
      </div>
    </div>
  );
}
