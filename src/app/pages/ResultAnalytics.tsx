import { useEffect, useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { BarChart3, Loader2 } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { recordsApi } from "../../lib/api";

type AnalyticsSummary = {
  total_applicants?: number;
  graded_applicants?: number;
  total_records?: number;
  graded_records?: number;
  avg_score?: number | null;
  pass_rate?: number | null;
  pass_count?: number;
  fail_count?: number;
  score_distribution?: {
    range: string;
    count: number;
  }[];
};

const defaultScoreDistribution = [
  { range: "0-20", count: 0 },
  { range: "21-40", count: 0 },
  { range: "41-60", count: 0 },
  { range: "61-80", count: 0 },
  { range: "81-100", count: 0 },
];

export default function ResultAnalytics() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);

  useEffect(() => {
    recordsApi
      .getAnalyticsSummary()
      .then((data) => {
        setSummary(data);
      })
      .catch(console.error)
      .finally(() => setLoadingStats(false));
  }, []);

  const totalApplicants =
    summary?.total_applicants ??
    summary?.graded_records ??
    0;

  const gradedApplicants =
    summary?.graded_applicants ??
    0;

  const passCount = summary?.pass_count ?? 0;

  const failCount =
    summary?.fail_count ??
    Math.max(totalApplicants - passCount, 0);

  const scoreDistribution = useMemo(() => {
    if (
      Array.isArray(summary?.score_distribution) &&
      summary.score_distribution.length > 0
    ) {
      return summary.score_distribution;
    }

    return defaultScoreDistribution;
  }, [summary]);

  const passRateData = useMemo(() => {
    if (!summary || totalApplicants <= 0) {
      return [];
    }

    return [
      { name: "합격", value: passCount, color: "#10b981" },
      { name: "불합격", value: failCount, color: "#ef4444" },
    ];
  }, [summary, totalApplicants, passCount, failCount]);

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800 flex items-center gap-2">
          <BarChart3 className="size-7 text-sky-600" />
          결과 분석
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          전체 응시자 시험 결과 및 합격 현황
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-6">
        <Card className="border-slate-200">
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-slate-600 mb-1">총 응시자</p>
              {loadingStats ? (
                <Loader2 className="size-6 animate-spin text-sky-500 mx-auto" />
              ) : (
                <p className="text-3xl font-semibold text-slate-800">
                  {totalApplicants}명
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-slate-600 mb-1">평균 점수</p>
              {loadingStats ? (
                <Loader2 className="size-6 animate-spin text-sky-500 mx-auto" />
              ) : (
                <p className="text-3xl font-semibold text-sky-700">
                  {summary?.avg_score != null ? `${summary.avg_score}점` : "-"}
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-slate-600 mb-1">합격률</p>
              {loadingStats ? (
                <Loader2 className="size-6 animate-spin text-sky-500 mx-auto" />
              ) : (
                <p className="text-3xl font-semibold text-green-700">
                  {summary?.pass_rate != null ? `${summary.pass_rate}%` : "-"}
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-slate-600 mb-1">합격자 수</p>
              {loadingStats ? (
                <Loader2 className="size-6 animate-spin text-sky-500 mx-auto" />
              ) : (
                <p className="text-3xl font-semibold text-violet-700">
                  {passCount}명
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6">
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-lg">점수 분포</CardTitle>
            <CardDescription>응시자별 점수 구간 분포</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={scoreDistribution}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="range" stroke="#64748b" fontSize={12} />
                <YAxis stroke="#64748b" fontSize={12} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#fff",
                    border: "1px solid #e2e8f0",
                    borderRadius: "8px",
                  }}
                />
                <Bar dataKey="count" fill="#0ea5e9" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-lg">합격/불합격 비율</CardTitle>
            <CardDescription>전체 응시자 합격 현황</CardDescription>
          </CardHeader>
          <CardContent>
            {passRateData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={passRateData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) =>
                      `${name} ${(percent * 100).toFixed(0)}%`
                    }
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {passRateData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-sm text-slate-500">
                분석할 응시 결과가 없습니다.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}