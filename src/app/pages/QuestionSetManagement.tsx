import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Search, Plus, Edit, Trash2 } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";

const questionSets = [
  {
    id: 1,
    name: "Spring Framework 핵심",
    role: "백엔드 개발자",
    level: "고급",
    questionCount: 45,
    createdDate: "2026-03-15",
  },
  {
    id: 2,
    name: "React 컴포넌트 설계",
    role: "프론트엔드 개발자",
    level: "중급",
    questionCount: 38,
    createdDate: "2026-03-12",
  },
  {
    id: 3,
    name: "데이터베이스 최적화",
    role: "백엔드 개발자",
    level: "고급",
    questionCount: 52,
    createdDate: "2026-03-10",
  },
  {
    id: 4,
    name: "REST API 디자인",
    role: "백엔드 개발자",
    level: "중급",
    questionCount: 40,
    createdDate: "2026-03-08",
  },
  {
    id: 5,
    name: "Python 데이터 분석",
    role: "데이터 엔지니어",
    level: "중급",
    questionCount: 35,
    createdDate: "2026-03-05",
  },
  {
    id: 6,
    name: "Kubernetes 운영",
    role: "DevOps 엔지니어",
    level: "고급",
    questionCount: 30,
    createdDate: "2026-03-03",
  },
  {
    id: 7,
    name: "JavaScript ES6+",
    role: "프론트엔드 개발자",
    level: "초급",
    questionCount: 28,
    createdDate: "2026-03-01",
  },
  {
    id: 8,
    name: "마이크로서비스 아키텍처",
    role: "백엔드 개발자",
    level: "고급",
    questionCount: 42,
    createdDate: "2026-02-28",
  },
];

export default function QuestionSetManagement() {
  const [searchTerm, setSearchTerm] = useState("");

  const filteredSets = questionSets.filter((set) =>
    set.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    set.role.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">문제 세트 관리</h1>
          <p className="text-sm text-slate-500 mt-1">문제 세트 목록 조회 및 관리</p>
        </div>
        <Button className="bg-sky-600 hover:bg-sky-700">
          <Plus className="size-4 mr-2" />
          세트 생성
        </Button>
      </div>

      <Card className="border-slate-200">
        <CardHeader className="border-b border-slate-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-slate-400" />
            <Input
              placeholder="세트명"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>세트명</TableHead>
                <TableHead>난이도</TableHead>
                <TableHead>문제 수</TableHead>
                <TableHead>생성일</TableHead>
                <TableHead className="text-right">작업</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredSets.map((set) => (
                <TableRow key={set.id}>
                  <TableCell className="font-medium">{set.name}</TableCell>
                  <TableCell>
                    <Badge
                      variant="secondary"
                      className={
                        set.level === "고급"
                          ? "bg-red-100 text-red-700"
                          : set.level === "중급"
                            ? "bg-amber-100 text-amber-700"
                            : "bg-green-100 text-green-700"
                      }
                    >
                      {set.level}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-slate-600">{set.questionCount}개</TableCell>
                  <TableCell className="text-slate-500 text-sm">{set.createdDate}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button variant="ghost" size="sm">
                        <Edit className="size-4 mr-2" />
                        수정
                      </Button>
                      <Button variant="ghost" size="sm" className="text-red-600 hover:text-red-700">
                        <Trash2 className="size-4 mr-2" />
                        삭제
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
