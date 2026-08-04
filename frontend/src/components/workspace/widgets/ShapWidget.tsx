import { useState, useEffect } from 'react';
import { useLoanStore } from '../../../store/useLoanStore';
import { Sparkles, HelpCircle, BarChart3, TrendingDown, TrendingUp } from 'lucide-react';
import { api } from '../../../lib/api';

export default function ShapWidget() {
  const { sessionId } = useLoanStore();
  const [loading, setLoading] = useState(true);
  const [shapData, setShapData] = useState<any>(null);

  useEffect(() => {
    if (sessionId) {
      api.fetchShapExplainability(sessionId).then((res) => {
        if (res.success && res.data?.shap_data) {
          setShapData(res.data.shap_data);
        }
        setLoading(false);
      });
    } else {
      // Fallback dummy SHAP data for demo/unauthenticated sessions
      setShapData({
        base_rate: 12.50,
        final_approved_rate: 10.50,
        final_approved_limit: 1500000,
        shap_summary: "Your approved interest rate of 10.50% p.a. includes a 2.0% discount for CIBIL score (800+) and a 0.25% discount for metropolitan location risk.",
        waterfall: [
          { feature: "Base Benchmark", rate_impact: 12.50, limit_impact: 300000, direction: "neutral", description: "National Benchmark Pricing for Personal Loans." },
          { feature: "CIBIL Bureau Score", rate_impact: -2.00, limit_impact: 500000, direction: "positive", description: "Tier-1 Prime Score (800+) reduced risk premium significantly." },
          { feature: "Monthly Net Income", rate_impact: -0.50, limit_impact: 450000, direction: "positive", description: "High income level qualified borrower for maximum leverage." },
          { feature: "FOIR / Existing Debt", rate_impact: -0.25, limit_impact: 150000, direction: "positive", description: "Healthy debt-service ratio leaves high disposable buffer." },
          { feature: "Location Tier", rate_impact: -0.25, limit_impact: 100000, direction: "positive", description: "Mumbai BKC address registered as low default metropolitan tier." }
        ]
      });
      setLoading(false);
    }
  }, [sessionId]);

  if (loading) {
    return (
      <div className="bg-[#111] border border-white/10 rounded-2xl p-6 flex flex-col items-center justify-center space-y-3">
        <div className="w-8 h-8 rounded-full border-2 border-emerald-500 border-t-transparent animate-spin" />
        <p className="text-xs text-white/50 font-mono uppercase tracking-wider">Computing Shapley Additive Explanations...</p>
      </div>
    );
  }

  return (
    <div className="bg-[#111] border border-white/10 rounded-2xl p-6 w-full max-w-2xl shadow-2xl relative overflow-hidden animate-fade-in group">
      <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 rounded-full blur-3xl group-hover:bg-emerald-500/10 transition-colors" />

      {/* Header */}
      <div className="flex justify-between items-center mb-6 relative z-10 border-b border-white/5 pb-4">
        <div>
          <h3 className="text-lg font-display font-medium text-white tracking-tight flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-emerald-400" />
            SHAP Credit Underwriting Explainability
          </h3>
          <p className="text-xs text-white/40 mt-1">Algorithmic pricing feature-level contributions (SHAP values)</p>
        </div>
        <span className="text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full flex items-center gap-1 font-medium font-mono">
          <Sparkles className="w-3 h-3" /> Explainable AI (XAI)
        </span>
      </div>

      <div className="space-y-6 relative z-10">
        {/* Summary Card */}
        <div className="bg-[#050505] p-4 rounded-xl border border-white/5 text-xs text-white/80 leading-relaxed font-sans">
          <strong>Decision Summary:</strong> {shapData?.shap_summary}
        </div>

        {/* Feature Impact Waterfall Rows */}
        <div className="space-y-3">
          <div className="grid grid-cols-12 text-[10px] font-bold uppercase tracking-wider text-white/40 font-mono pb-2 border-b border-white/5">
            <span className="col-span-4">Feature Risk Variable</span>
            <span className="col-span-3 text-right">Interest Rate Impact</span>
            <span className="col-span-5 pl-4">Impact Rationale</span>
          </div>

          {shapData?.waterfall?.map((row: any, idx: number) => {
            const isRateDiscount = row.rate_impact < 0;
            const isBase = row.feature === 'Base Benchmark';
            return (
              <div key={idx} className="grid grid-cols-12 items-center text-xs py-2.5 border-b border-white/5 hover:bg-white/[0.01] transition-all rounded-lg px-1">
                <span className="col-span-4 font-semibold text-white/90">{row.feature}</span>
                <span className={`col-span-3 text-right font-mono font-bold ${
                  isBase ? 'text-white' : isRateDiscount ? 'text-emerald-400' : 'text-rose-400'
                }`}>
                  {isBase ? `${row.rate_impact.toFixed(2)}%` : `${isRateDiscount ? '' : '+'}${row.rate_impact.toFixed(2)}% p.a.`}
                </span>
                <span className="col-span-5 pl-4 text-white/50 text-[11px] leading-snug">
                  {row.description}
                </span>
              </div>
            );
          })}
        </div>

        {/* Dynamic Metric Comparison */}
        <div className="grid grid-cols-2 gap-4 pt-4 border-t border-white/5 text-center">
          <div className="bg-[#0A0A0A] p-4 rounded-xl border border-white/5">
            <p className="text-[10px] text-white/40 uppercase tracking-widest font-bold font-mono">Market Reference Rate</p>
            <p className="text-xl font-bold text-white mt-1">{shapData?.base_rate.toFixed(2)}% p.a.</p>
          </div>
          <div className="bg-emerald-500/5 p-4 rounded-xl border border-emerald-500/10">
            <p className="text-[10px] text-emerald-400 uppercase tracking-widest font-bold font-mono">Your Approved Rate</p>
            <p className="text-xl font-bold text-emerald-400 mt-1">{shapData?.final_approved_rate.toFixed(2)}% p.a.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
