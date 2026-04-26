import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { BarChart3, TrendingDown, Sparkles, Award, Loader2 } from "lucide-react";
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
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts";
import { recordsApi, dashboardApi } from "../../lib/api";
import type { WeakCompetency } from "../../lib/types";

// 차트 정적 데이터 (AI 기능 추가 전 임시)
const scoreDistribution = [
  { range: "0-20", count: 0 },
  { range: "21-40", count: 0 },
  { range: "41-60", count: 0 },
  { range: "61-80", count: 0 },
  { range: "81-100", count: 0 },
];

const weakAreas = [
  { area: "데이터베이스 최적화", avgScore: 65, affectedApplicants: 38, commonIssues: ["N+1 쿼리 문제", "인덱스 설계", "쿼리 최적화"] },
  { area: "보안 구현", avgScore: 71, affectedApplicants: 40, commonIssues: ["CSRF 방어", "SQL Injection 예방", "인증/인가 메커니즘"] },
  { area: "REST API 설계", avgScore: 78, affectedApplicants: 42, commonIssues: ["HTTP 메서드 선택", "상태 코드 활용", "버저닝 전략"] },
];

const aiAnalysis = `AI 분석 기능은 추후 LangGraph + OpenAI API 연동 시 활성화됩니다. 현재는 집계된 통계 데이터를 기반으로 역량별 분석 정보를 제공합니다.`;

const interviewQuestions = [
  "실제 프로젝트에서 데이터베이스 성능 문제를 해결한 경험을 설명해 주세요.",
  "N+1 쿼리 문제를 발견하고 해결한 구체적인 사례가 있나요?",
  "웹 애플리케이션에서 보안 취약점을 어떻게 예방하고 있나요?",
  "CSRF와 XSS 공격의 차이점과 각각의 방어 전략을 설명해 주세요.",
];

const followUpAreas = [
  { area: "데이터베이스 최적화 심화", priority: "높음", topics: ["쿼리 플랜 분석", "인덱스 전략", "커넥션 풀 관리"] },
  { area: "보안 실무 강화", priority: "높음", topics: ["OWASP Top 10", "인증/인가 패턴", "암호화 구현"] },
  { area: "API 설계 고급", priority: "중간", topics: ["RESTful 성숙도 모델", "HATEOAS", "GraphQL 비교"] },
];

export default function ResultAnalytics() {
  const [summary, setSummary] = useState<any>(null);
  const [weakComps, setWeakComps] = useState<WeakCompetency[]>([]);
  const [loadingStats, setLoadingStats] = useState(true);

  useEffect(() => {
    Promise.all([
      recordsApi.getAnalyticsSummary(),
      dashboardApi.getWeakCompetencies(),
    ])
      .then(([s, w]) => { setSummary(s); setWeakComps(w); })
      .catch(console.error)
      .finally(() => setLoadingStats(false));
  }, []);

  const passRateData = summary ? [
    { name: "합격", value: summary.pass_count, color: "#10b981" },
    { name: "불합격", value: summary.graded_records - summary.pass_count, color: "#ef4444" },
  ] : [];

  const competencyChartData = weakComps.map((c) => ({
    competency: c.competency,
    avgScore: c.avg_score,
    count: c.count,
  }));

  const radarData = weakComps.map((c) => ({
    subject: c.competency.length > 6 ? c.competency.slice(0, 6) + ".." : c.competency,
    score: c.avg_score,
    fullMark: 100,
  }));

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800 flex items-center gap-2">
          <BarChart3 className="size-7 text-sky-600" />
          결과 분석
        </h1>
        <p className="text-sm text-slate-500 mt-1">전체 응시자 시험 결과 및 역량 분석</p>
      </div>

      {/* Score Overview */}
      <div className="grid grid-cols-4 gap-6">
        <Card className="border-slate-200">
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-slate-600 mb-1">총 응시자</p>
              {loadingStats ? <Loader2 className="size-6 animate-spin text-sky-500 mx-auto" /> : <p className="text-3xl font-semibold text-slate-800">{summary?.graded_records ?? 0}명</p>}
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-200">
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-slate-600 mb-1">평균 점수</p>
              {loadingStats ? <Loader2 className="size-6 animate-spin text-sky-500 mx-auto" /> : <p className="text-3xl font-semibold text-sky-700">{summary?.avg_score != null ? `${summary.avg_score}점` : "-"}</p>}
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-200">
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-slate-600 mb-1">합격률</p>
              {loadingStats ? <Loader2 className="size-6 animate-spin text-sky-500 mx-auto" /> : <p className="text-3xl font-semibold text-green-700">{summary?.pass_rate != null ? `${summary.pass_rate}%` : "-"}</p>}
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-200">
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-slate-600 mb-1">합격자 수</p>
              {loadingStats ? <Loader2 className="size-6 animate-spin text-sky-500 mx-auto" /> : <p className="text-3xl font-semibold text-violet-700">{summary?.pass_count ?? 0}명</p>}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6">
        {/* Score Distribution */}
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
                <YAxis stroke="#64748b" fontSize={12} />
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

        {/* Pass Rate */}
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-lg">합격/불합격 비율</CardTitle>
            <CardDescription>전체 응시자 합격 현황</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={passRateData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
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
          </CardContent>
        </Card>

        {/* Competency Distribution */}
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-lg">역량별 평균 점수</CardTitle>
            <CardDescription>각 역량 영역별 평균 성과</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={competencyChartData.length > 0 ? competencyChartData : [{ competency: "데이터 없음", avgScore: 0, count: 0 }]} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" stroke="#64748b" fontSize={12} />
                <YAxis type="category" dataKey="competency" stroke="#64748b" fontSize={12} width={150} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#fff",
                    border: "1px solid #e2e8f0",
                    borderRadius: "8px",
                  }}
                />
                <Bar dataKey="avgScore" fill="#8b5cf6" radius={[0, 8, 8, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Radar Chart */}
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-lg">역량 레이더 차트</CardTitle>
            <CardDescription>전체 역량 균형 분석</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#e2e8f0" />
                <PolarAngleAxis dataKey="subject" stroke="#64748b" fontSize={11} />
                <PolarRadiusAxis stroke="#64748b" fontSize={11} />
                <Radar
                  name="평균 점수"
                  dataKey="score"
                  stroke="#0ea5e9"
                  fill="#0ea5e9"
                  fillOpacity={0.6}
                />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Weak Areas */}
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <TrendingDown className="size-5 text-amber-600" />
            취약 영역 상세 분석
          </CardTitle>
          <CardDescription>개선이 필요한 역량 영역</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {weakAreas.map((area, idx) => (
              <div key={idx} className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-base font-semibold text-slate-800">{area.area}</h3>
                    <p className="text-sm text-slate-600 mt-1">
                      {area.affectedApplicants}명의 응시자 영향
                    </p>
                  </div>
                  <Badge variant="secondary" className="bg-amber-100 text-amber-700">
                    평균 {area.avgScore}점
                  </Badge>
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-700 mb-2">주요 취약 주제</p>
                  <div className="flex items-center gap-2">
                    {area.commonIssues.map((issue, i) => (
                      <Badge key={i} variant="secondary" className="bg-white text-slate-700">
                        {issue}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-6">
        {/* AI Analysis */}
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Sparkles className="size-5 text-violet-600" />
              AI 종합 분석
            </CardTitle>
            <CardDescription>LLM 기반 결과 인사이트</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-700 leading-relaxed">{aiAnalysis}</p>
          </CardContent>
        </Card>

        {/* Recommended Interview Questions */}
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Award className="size-5 text-sky-600" />
              추천 면접 질문
            </CardTitle>
            <CardDescription>취약 영역 기반 심화 질문</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {interviewQuestions.map((q, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <span className="size-6 flex-shrink-0 flex items-center justify-center rounded-full bg-sky-100 text-sky-700 text-sm font-medium">
                    {idx + 1}
                  </span>
                  <p className="text-sm text-slate-700 leading-relaxed">{q}</p>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Follow-up Areas */}
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="text-lg">추천 후속 학습 영역</CardTitle>
          <CardDescription>취약 역량 개선을 위한 학습 방향</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            {followUpAreas.map((area, idx) => (
              <div key={idx} className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                <div className="flex items-start justify-between mb-3">
                  <h3 className="text-sm font-semibold text-slate-800">{area.area}</h3>
                  <Badge
                    variant="secondary"
                    className={
                      area.priority === "높음"
                        ? "bg-red-100 text-red-700"
                        : "bg-amber-100 text-amber-700"
                    }
                  >
                    {area.priority}
                  </Badge>
                </div>
                <ul className="space-y-1">
                  {area.topics.map((topic, i) => (
                    <li key={i} className="text-sm text-slate-600 flex items-start gap-2">
                      <span className="text-sky-600">•</span>
                      <span>{topic}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
