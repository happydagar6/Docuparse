'use client';

export default function QuizLayout({ children }) {
    return (
        <div className="min-h-screen bg-linear-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
            <div className="container mx-auto px-4 py-8">
                {children}
            </div>
        </div>
    );
}