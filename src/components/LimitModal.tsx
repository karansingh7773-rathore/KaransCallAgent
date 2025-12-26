import { AlertTriangle } from 'lucide-react';

export function LimitModal() {
    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/95 backdrop-blur-md animate-in fade-in duration-300">
            <div className="w-full max-w-md bg-zinc-900 border border-red-500/30 rounded-2xl p-8 text-center shadow-2xl relative animate-in zoom-in-95 duration-300">

                <div className="mx-auto w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mb-6">
                    <AlertTriangle className="w-8 h-8 text-red-500" />
                </div>

                <h2 className="text-2xl font-bold text-white mb-4">Demo Limit Reached</h2>

                <p className="text-zinc-400 mb-8 leading-relaxed">
                    You have reached your limit for this demo session.
                    <br />
                    <span className="text-zinc-500 text-sm mt-2 block">
                        Please contact <span className="text-zinc-300 font-medium">Karan</span> for more credits.
                    </span>
                </p>

                <div className="p-4 bg-zinc-950/50 rounded-xl border border-zinc-800">
                    <p className="text-xs text-zinc-500">
                        Thank you for trying out Sentinel Connect.
                    </p>
                </div>
            </div>
        </div>
    );
}
