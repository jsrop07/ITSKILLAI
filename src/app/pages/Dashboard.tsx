import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { useNavigate } from "react-router";
import {
  Users,
  ClipboardList,
  FileCheck,
  Sparkles,
  TrendingDown,
  ArrowRight,
  Loader2,
} from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { dashboardApi } from "../../lib/api";
import type { DashboardStats, RecentExamRecord, WeakCompetency } from "../../lib/types";

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentExams, setRecentExams] = useState<RecentExamRecord[]>([]);
  const [weakCompetencies, setWeakCompetencies] = useState<WeakCompetency[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [s, r, w] = await Promise.all([
          dashboardApi.getStats(),
          dashboardApi.getRecentRecords(5),
          dashboardApi.getWeakCompetencies(),
        ]);
        setStats(s);
        setRecentExams(r);
        setWeakCompetencies(w);
      } catch (err) {
        console.error("대시보드 데이터 로딩 실패:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const kpiData = stats
    ? [
      { label: "전체 응시자", value: String(stats.total_applicants), icon: Users, color: "text-sky-600", bg: "bg-sky-50" },
      { label: "진행 중인 시험", value: String(stats.in_progress_exams), icon: ClipboardList, color: "text-blue-600", bg: "bg-blue-50" },
      { label: "검토 대기 문제", value: String(stats.pending_review_questions), icon: FileCheck, color: "text-amber-600", bg: "bg-amber-50" },
      { label: "AI 생성 문제", value: String(stats.recent_question_count), icon: Sparkles, color: "text-violet-600", bg: "bg-violet-50" },
    ]
    : [];

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-96">
        <Loader2 className="size-8 animate-spin text-sky-500" />
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800">대시보드</h1>
        <p className="text-sm text-slate-500 mt-1">전체 시스템 현황 및 주요 지표</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-6">
        {kpiData.map((kpi) => (
          <Card key={kpi.label} className="border-slate-200">
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-slate-600 mb-1">{kpi.label}</p>
                  <p className="text-3xl font-semibold text-slate-800">{kpi.value}</p>
                </div>
                <div className={`${kpi.bg} p-3 rounded-lg`}>
                  <kpi.icon className={`size-6 ${kpi.color}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Actions */}
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="text-lg">빠른 작업</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4">
            <Button
              variant="outline"
              className="h-auto py-4 flex flex-col gap-2 border-sky-200 hover:bg-sky-50 hover:border-sky-300"
              onClick={() => navigate("/ai-generation")}
            >
              <Sparkles className="size-5 text-sky-600" />
              <span className="text-sm">AI 문제 생성</span>
            </Button>
            <Button
              variant="outline"
              className="h-auto py-4 flex flex-col gap-2 border-slate-200 hover:bg-slate-50"
              onClick={() => navigate("/ai-review")}
            >
              <FileCheck className="size-5 text-slate-600" />
              <span className="text-sm">AI 문제 검토</span>
            </Button>
            <Button
              variant="outline"
              className="h-auto py-4 flex flex-col gap-2 border-slate-200 hover:bg-slate-50"
              onClick={() => navigate("/exams")}
            >
              <ClipboardList className="size-5 text-slate-600" />
              <span className="text-sm">시험 관리</span>
            </Button>
            <Button
              variant="outline"
              className="h-auto py-4 flex flex-col gap-2 border-slate-200 hover:bg-slate-50"
              onClick={() => navigate("/analytics")}
            >
              <TrendingDown className="size-5 text-slate-600" />
              <span className="text-sm">결과 분석</span>
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-3 gap-6">
        {/* Recent Exam Results */}
        <Card className="col-span-2 border-slate-200">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">최근 시험 결과</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => navigate("/applicants")}>
                전체 보기 <ArrowRight className="size-4 ml-2" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {recentExams.length === 0 ? (
              <p className="text-sm text-slate-400 py-8 text-center">시험 결과가 없습니다.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>응시자</TableHead>
                    {/* <TableHead>직무</TableHead> */}
                    <TableHead>시험</TableHead>
                    <TableHead>점수</TableHead>
                    <TableHead>결과</TableHead>
                    <TableHead>날짜</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentExams.map((exam) => (
                    <TableRow
                      key={exam.record_id}
                      className="cursor-pointer hover:bg-slate-50"
                      onClick={() => navigate(`/applicants/${exam.applicant_id}`)}
                    >
                      <TableCell className="font-medium">{exam.name}</TableCell>
                      <TableCell className="text-slate-600">{exam.exam}</TableCell>
                      <TableCell>
                        {exam.score != null ? (
                          <Badge
                            variant="secondary"
                            className={
                              exam.score >= 90
                                ? "bg-green-100 text-green-700"
                                : exam.score >= 80
                                  ? "bg-sky-100 text-sky-700"
                                  : "bg-amber-100 text-amber-700"
                            }
                          >
                            {exam.score}점
                          </Badge>
                        ) : (
                          <span className="text-slate-400 text-sm">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {exam.pass_yn != null && (
                          <Badge
                            variant="secondary"
                            className={exam.pass_yn ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}
                          >
                            {exam.pass_yn ? "합격" : "불합격"}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-slate-500 text-sm">{exam.submitted_at || "-"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Weak Competencies */}
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingDown className="size-5 text-amber-600" />
              취약 역량 요약
            </CardTitle>
            <CardDescription>평균 점수가 낮은 역량 영역</CardDescription>
          </CardHeader>
          <CardContent>
            {weakCompetencies.length === 0 ? (
              <p className="text-sm text-slate-400 py-4 text-center">데이터가 없습니다.</p>
            ) : (
              <div className="space-y-4">
                {weakCompetencies.map((item, idx) => (
                  <div key={idx} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-slate-700">{item.competency}</p>
                      <Badge variant="secondary" className="bg-amber-100 text-amber-700">
                        {item.avg_score}점
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-amber-500 rounded-full"
                          style={{ width: `${item.avg_score}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-500">{item.count}명</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
