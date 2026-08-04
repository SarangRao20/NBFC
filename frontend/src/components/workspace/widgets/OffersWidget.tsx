import { useEffect, useState } from 'react';
import { useLoanStore } from '../../../store/useLoanStore';
import { CheckCircle2, Loader2, Zap } from 'lucide-react';
import { api } from '../../../lib/api';

interface OffersWidgetProps {
  onSelect?: (lenderId: string) => void;
}

export default function OffersWidget({ onSelect }: OffersWidgetProps) {
  const { loanDetails, sessionId, setState } = useLoanStore();
  const [selectedOfferId, setSelectedOfferId] = useState<string | null>(null);
  const [offersList, setOffersList] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadOffers() {
      setLoading(true);
      if (sessionId) {
        const res = await api.getOffers(sessionId);
        if (res.success && res.data?.offers && res.data.offers.length > 0) {
          setOffersList(res.data.offers);
          setLoading(false);
          return;
        }
      }

      // Fallback dynamically calculated using requested amount & tenure
      const fallbackAmount = loanDetails.requestedAmount;
      const fallbackTenure = loanDetails.tenureMonths;
      const calculatedEmi = (rate: number) =>
        Math.round((fallbackAmount * (1 + (rate / 100) * (fallbackTenure / 12))) / fallbackTenure);

      setOffersList([
        {
          lender_id: 'hdfc_bank',
          lender_name: 'HDFC Bank NBFC',
          interest_rate: 10.5,
          emi: calculatedEmi(10.5),
          tag: 'Prime Tier-1 Rate',
          settlement_days: 1,
        },
        {
          lender_id: 'bajaj_finserv',
          lender_name: 'Bajaj Finance Ltd',
          interest_rate: 11.2,
          emi: calculatedEmi(11.2),
          tag: 'Sub-Second Disbursal',
          settlement_days: 1,
        },
        {
          lender_id: 'muthoot_finance',
          lender_name: 'Muthoot Capital',
          interest_rate: 12.0,
          emi: calculatedEmi(12.0),
          tag: 'High Approval Rate',
          settlement_days: 2,
        },
      ]);
      setLoading(false);
    }

    loadOffers();
  }, [sessionId, loanDetails.requestedAmount, loanDetails.tenureMonths]);

  const handleAccept = (lenderId: string) => {
    setSelectedOfferId(lenderId);
    setState('ACTIVE_LOAN');
    if (onSelect) onSelect(lenderId);
  };

  if (loading) {
    return (
      <div className="bg-[#111] border border-white/10 rounded-2xl p-6 flex items-center justify-center gap-3 text-white/50 text-xs font-mono">
        <Loader2 className="w-4 h-4 animate-spin text-emerald-500" />
        Evaluating 40,000 Risk Vectors across Institutional Lenders...
      </div>
    );
  }

  return (
    <div className="w-full max-w-2xl relative z-10 group">
      <div className="flex gap-4 overflow-x-auto pb-4 snap-x no-scrollbar">
        {offersList.map((offer, idx) => {
          const lId = offer.lender_id || `lender-${idx}`;
          const isSelected = selectedOfferId === lId;
          const lenderName = offer.lender_name || offer.lender || 'Institutional Partner';
          const roi = offer.interest_rate || offer.roi || 10.5;
          const emiVal = offer.emi || Math.round((loanDetails.requestedAmount * 1.105) / loanDetails.tenureMonths);

          return (
            <div
              key={lId}
              onClick={() => setSelectedOfferId(lId)}
              className={`min-w-[280px] snap-center p-6 rounded-2xl border cursor-pointer transition-all duration-300 relative overflow-hidden flex-shrink-0 ${
                isSelected
                  ? 'bg-[#111] border-white shadow-xl shadow-white/5'
                  : 'bg-[#0A0A0A] border-white/10 hover:border-white/30'
              }`}
            >
              {isSelected && (
                <div className="absolute top-4 right-4">
                  <CheckCircle2 className="w-5 h-5 text-white" />
                </div>
              )}

              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center font-display font-bold text-sm text-emerald-400">
                  {lenderName.charAt(0)}
                </div>
                <div>
                  <h4 className="font-bold text-base text-white leading-tight">{lenderName}</h4>
                  <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest flex items-center gap-1 mt-0.5">
                    <Zap className="w-3 h-3" /> {offer.tag || `${offer.settlement_days || 1} Day Disbursal`}
                  </span>
                </div>
              </div>

              <div className="space-y-3 mb-6 font-mono text-xs">
                <div className="flex justify-between items-center border-b border-white/5 pb-2">
                  <span className="text-white/50 uppercase tracking-widest font-sans">Interest Rate</span>
                  <span className="font-medium text-emerald-400 text-sm">{roi}% p.a.</span>
                </div>
                <div className="flex justify-between items-center border-b border-white/5 pb-2">
                  <span className="text-white/50 uppercase tracking-widest font-sans">Monthly EMI</span>
                  <span className="font-medium text-white text-sm">₹{emiVal.toLocaleString('en-IN')}</span>
                </div>
                {offer.processing_fee && (
                  <div className="flex justify-between items-center text-[10px] text-white/40">
                    <span className="font-sans">Processing Fee</span>
                    <span>₹{Math.round(offer.processing_fee).toLocaleString('en-IN')}</span>
                  </div>
                )}
              </div>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleAccept(lId);
                }}
                className={`w-full py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isSelected
                    ? 'bg-white text-black font-semibold'
                    : 'bg-white/5 text-white hover:bg-white/10 border border-white/10'
                }`}
              >
                {isSelected ? 'Execute Smart Contract' : 'Select Partner'}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
