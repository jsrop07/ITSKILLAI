import { Sparkles } from "lucide-react";
import { Card } from "../ui/card";
import { Button } from "../ui/button";

type AIReportCardProps = {
    report?: string | null;
    title?: string;
    description?: string;
    actionLabel?: string;
    actionLoadingLabel?: string;
    loading?: boolean;
    onAction?: () => void;
};

type ParsedReportItem =
    | { type: "section"; key: number; text: string }
    | { type: "number"; key: number; number: string; text: string }
    | { type: "bullet"; key: number; text: string }
    | { type: "paragraph"; key: number; text: string };

function parseReport(report: string): ParsedReportItem[] {
    const lines = report
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);

    return lines.map((line, index) => {
        const isSection =
            line === "[종합 진단]" ||
            line === "[부족한 세부 영역]" ||
            line === "[추천 학습 순서]";

        if (isSection) {
            return {
                type: "section",
                key: index,
                text: line.replace("[", "").replace("]", ""),
            };
        }

        if (/^\d+\./.test(line)) {
            return {
                type: "number",
                key: index,
                number: line.split(".")[0],
                text: line.replace(/^\d+\.\s*/, ""),
            };
        }

        if (line.startsWith("-")) {
            return {
                type: "bullet",
                key: index,
                text: line.replace(/^-/, "").trim(),
            };
        }

        return {
            type: "paragraph",
            key: index,
            text: line,
        };
    });
}

function getSectionIndex(text: string) {
    if (text === "종합 진단" || text === "전체 진단 요약") return "1";
    if (text === "부족한 세부 영역" || text === "부족한 세부 영역 분석") return "2";
    if (text === "추천 학습 순서") return "3";
    return "";
}

export default function AIReportCard({
    report,
    title = "AI 종합 진단 리포트",
    description = "정오답 패턴과 문제 내용을 기반으로 생성된 맞춤형 분석입니다.",
    actionLabel,
    actionLoadingLabel = "생성 중...",
    loading = false,
    onAction,
}: AIReportCardProps) {
    if (!report && !onAction) return null;

    const parsed = report ? parseReport(report) : [];

    return (
        <Card className="!gap-0 !py-0 overflow-hidden border border-blue-100 bg-white shadow-sm">
            <div className="flex items-center justify-between gap-4 border-b border-blue-100 bg-blue-50 px-4 py-2.5">
                <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
                        AI
                    </div>

                    <div className="min-w-0">
                        <h2 className="text-sm font-semibold text-slate-900">
                            {title}
                        </h2>
                        <p className="mt-0.5 text-xs text-slate-600">
                            {description}
                        </p>
                    </div>
                </div>

                {onAction && (
                    <Button
                        type="button"
                        size="sm"
                        variant={report ? "outline" : "default"}
                        onClick={onAction}
                        disabled={loading}
                        className="h-8 shrink-0 gap-1.5 px-3 text-xs"
                    >
                        <Sparkles className="h-3.5 w-3.5" />
                        {loading
                            ? actionLoadingLabel
                            : actionLabel || (report ? "리포트 재생성" : "AI 리포트 생성")}
                    </Button>
                )}
            </div>

            {report ? (
                <div className="bg-slate-50 px-4 py-3">
                    <div className="space-y-1.5 text-sm leading-6 text-slate-700">
                        {parsed.map((item) => {
                            if (item.type === "section") {
                                const sectionIndex = getSectionIndex(item.text);

                                return (
                                    <div key={item.key} className="pt-3 first:pt-0">
                                        <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2">
                                            {sectionIndex && (
                                                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-sky-100 text-xs font-bold text-sky-700">
                                                    {sectionIndex}
                                                </span>
                                            )}
                                            <h3 className="text-sm font-semibold text-slate-800">
                                                {item.text}
                                            </h3>
                                        </div>
                                    </div>
                                );
                            }
                            if (item.type === "number") {
                                return (
                                    <div
                                        key={item.key}
                                        className="flex gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2"
                                    >
                                        <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
                                            {item.number}
                                        </span>
                                        <p className="text-slate-700">{item.text}</p>
                                    </div>
                                );
                            }

                            if (item.type === "bullet") {
                                return (
                                    <div key={item.key} className="flex gap-2 pl-1">
                                        <span className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                                        <p>{item.text}</p>
                                    </div>
                                );
                            }

                            return (
                                <p key={item.key} className="pl-1 text-slate-700">
                                    {item.text}
                                </p>
                            );
                        })}
                    </div>
                </div>
            ) : (
                <div className="bg-slate-50 px-4 py-3">
                    <div className="rounded-lg border border-dashed border-blue-200 bg-white px-4 py-3 text-sm text-slate-600">
                        아직 AI 리포트가 생성되지 않았습니다. 버튼을 눌러 응시자의 정오답 패턴 기반 분석을 생성할 수 있습니다.
                    </div>
                </div>
            )}
        </Card>
    );
}