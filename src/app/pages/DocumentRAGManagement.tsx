import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Textarea } from "../components/ui/textarea";
import {
  FileText,
  Upload,
  RefreshCw,
  Database,
  Search,
  CheckCircle2,
  Clock,
  AlertCircle,
  Sparkles,
} from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";

const documents = [
  {
    id: 1,
    name: "Spring Framework 공식 가이드",
    type: "PDF",
    role: "백엔드 개발자",
    uploadDate: "2026-03-15",
    size: "2.4 MB",
    status: "인덱싱 완료",
    chunks: 145,
    lastIndexed: "2026-03-15 14:30",
  },
  {
    id: 2,
    name: "JPA 프로그래밍 레퍼런스",
    type: "PDF",
    role: "백엔드 개발자",
    uploadDate: "2026-03-12",
    size: "1.8 MB",
    status: "인덱싱 완료",
    chunks: 98,
    lastIndexed: "2026-03-12 16:45",
  },
  {
    id: 3,
    name: "React 공식 문서",
    type: "DOCX",
    role: "프론트엔드 개발자",
    uploadDate: "2026-03-10",
    size: "1.2 MB",
    status: "인덱싱 중",
    chunks: 0,
    lastIndexed: "-",
  },
  {
    id: 4,
    name: "웹 보안 베스트 프랙티스",
    type: "PDF",
    role: "전체",
    uploadDate: "2026-03-08",
    size: "3.1 MB",
    status: "인덱싱 완료",
    chunks: 182,
    lastIndexed: "2026-03-08 11:20",
  },
  {
    id: 5,
    name: "Kubernetes 운영 가이드",
    type: "PDF",
    role: "DevOps 엔지니어",
    uploadDate: "2026-03-05",
    size: "4.5 MB",
    status: "인덱싱 완료",
    chunks: 256,
    lastIndexed: "2026-03-05 09:15",
  },
  {
    id: 6,
    name: "Python 데이터 처리 실무",
    type: "PDF",
    role: "데이터 엔지니어",
    uploadDate: "2026-03-01",
    size: "2.9 MB",
    status: "인덱싱 실패",
    chunks: 0,
    lastIndexed: "-",
  },
];

const chunkPreviewData = [
  {
    id: 1,
    content:
      "Spring Framework에서 트랜잭션 관리는 @Transactional 애노테이션을 통해 선언적으로 수행할 수 있습니다. 이는 AOP(Aspect-Oriented Programming)를 기반으로 동작하며...",
    page: 24,
    tokens: 128,
  },
  {
    id: 2,
    content:
      "트랜잭션 전파(Propagation) 옵션은 여러 트랜잭션 메서드가 중첩될 때의 동작을 정의합니다. REQUIRED는 기본값으로, 기존 트랜잭션이 있으면 참여하고 없으면 새로 생성합니다...",
    page: 25,
    tokens: 142,
  },
  {
    id: 3,
    content:
      "REQUIRES_NEW 옵션은 항상 새로운 트랜잭션을 시작하며, 기존 트랜잭션이 있는 경우 이를 일시 중단합니다. 이는 독립적인 트랜잭션 처리가 필요할 때 유용합니다...",
    page: 27,
    tokens: 135,
  },
];

export default function DocumentRAGManagement() {
  const [searchQuery, setSearchQuery] = useState("");
  const [retrievalResults, setRetrievalResults] = useState<typeof chunkPreviewData>([]);
  const [selectedDoc, setSelectedDoc] = useState<number | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const handleRetrievalTest = () => {
    setIsSearching(true);
    setTimeout(() => {
      setRetrievalResults(chunkPreviewData);
      setIsSearching(false);
    }, 1000);
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800 flex items-center gap-2">
            <FileText className="size-7 text-sky-600" />
            문서 / RAG 관리
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            ChromaDB 벡터 검색 및 문서 인덱싱 관리
          </p>
        </div>
        <Button className="bg-sky-600 hover:bg-sky-700">
          <Upload className="size-4 mr-2" />
          문서 업로드
        </Button>
      </div>

      {/* ChromaDB Info Banner */}
      <Card className="border-violet-200 bg-gradient-to-r from-violet-50 to-sky-50">
        <CardContent className="py-4">
          <div className="flex items-center gap-4">
            <div className="size-12 rounded-full bg-violet-100 flex items-center justify-center">
              <Database className="size-6 text-violet-600" />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-slate-800">ChromaDB 벡터 데이터베이스</h3>
              <p className="text-sm text-slate-600 mt-0.5">
                OpenAI Embeddings를 활용한 하이브리드 RAG 검색 엔진
              </p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-violet-700">
                {documents.reduce((acc, doc) => acc + doc.chunks, 0)}
              </p>
              <p className="text-xs text-slate-600">총 벡터 청크</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-sky-700">{documents.length}</p>
              <p className="text-xs text-slate-600">인덱싱된 문서</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Document List */}
      <Card className="border-slate-200">
        <CardHeader className="border-b border-slate-200">
          <CardTitle className="text-lg">업로드된 문서 목록</CardTitle>
          <CardDescription>RAG 시스템에 인덱싱된 소스 문서</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>문서명</TableHead>
                <TableHead>유형</TableHead>
                <TableHead>관련 직무</TableHead>
                <TableHead>업로드일</TableHead>
                <TableHead>크기</TableHead>
                <TableHead>인덱싱 상태</TableHead>
                <TableHead>청크 수</TableHead>
                <TableHead className="text-right">작업</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {documents.map((doc) => (
                <TableRow key={doc.id}>
                  <TableCell className="font-medium flex items-center gap-2">
                    <FileText className="size-4 text-slate-400" />
                    {doc.name}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="bg-blue-100 text-blue-700">
                      {doc.type}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="bg-sky-100 text-sky-700">
                      {doc.role}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-slate-500 text-sm">{doc.uploadDate}</TableCell>
                  <TableCell className="text-slate-600">{doc.size}</TableCell>
                  <TableCell>
                    <Badge
                      variant="secondary"
                      className={
                        doc.status === "인덱싱 완료"
                          ? "bg-green-100 text-green-700"
                          : doc.status === "인덱싱 중"
                          ? "bg-blue-100 text-blue-700"
                          : "bg-red-100 text-red-700"
                      }
                    >
                      {doc.status === "인덱싱 완료" && (
                        <CheckCircle2 className="size-3 mr-1" />
                      )}
                      {doc.status === "인덱싱 중" && <Clock className="size-3 mr-1" />}
                      {doc.status === "인덱싱 실패" && <AlertCircle className="size-3 mr-1" />}
                      {doc.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-slate-600">
                    {doc.chunks > 0 ? `${doc.chunks}개` : "-"}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedDoc(doc.id)}
                        disabled={doc.chunks === 0}
                      >
                        청크 보기
                      </Button>
                      <Button variant="ghost" size="sm">
                        <RefreshCw className="size-4 mr-2" />
                        재인덱싱
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Retrieval Test */}
      <div className="grid grid-cols-2 gap-6">
        <Card className="border-slate-200">
          <CardHeader className="border-b border-slate-200">
            <CardTitle className="text-lg flex items-center gap-2">
              <Sparkles className="size-5 text-violet-600" />
              RAG 검색 테스트
            </CardTitle>
            <CardDescription>ChromaDB 벡터 검색 동작 확인</CardDescription>
          </CardHeader>
          <CardContent className="pt-6 space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">검색 쿼리</label>
              <Textarea
                placeholder="예: Spring Boot에서 트랜잭션을 관리하는 방법"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                rows={3}
                className="resize-none"
              />
            </div>
            <Button
              className="w-full bg-violet-600 hover:bg-violet-700"
              onClick={handleRetrievalTest}
              disabled={isSearching || !searchQuery}
            >
              {isSearching ? (
                <>
                  <RefreshCw className="size-4 mr-2 animate-spin" />
                  검색 중...
                </>
              ) : (
                <>
                  <Search className="size-4 mr-2" />
                  벡터 검색 실행
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader className="border-b border-slate-200">
            <CardTitle className="text-lg flex items-center gap-2">
              <Database className="size-5 text-sky-600" />
              검색 결과
            </CardTitle>
            <CardDescription>
              {retrievalResults.length > 0
                ? `${retrievalResults.length}개 관련 청크 발견`
                : "검색 대기 중"}
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4">
            {retrievalResults.length > 0 ? (
              <div className="space-y-3">
                {retrievalResults.map((result, idx) => (
                  <div
                    key={result.id}
                    className="p-3 bg-gradient-to-r from-violet-50 to-sky-50 border border-violet-200 rounded-lg"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <Badge variant="secondary" className="bg-violet-100 text-violet-700">
                        Chunk #{result.id} (Page {result.page})
                      </Badge>
                      <Badge variant="secondary" className="bg-sky-100 text-sky-700">
                        {result.tokens} tokens
                      </Badge>
                    </div>
                    <p className="text-sm text-slate-700 leading-relaxed">{result.content}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Database className="size-12 text-slate-300 mx-auto mb-3" />
                <p className="text-sm text-slate-500">
                  검색 쿼리를 입력하고 '벡터 검색 실행'을 클릭하세요
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Chunk Preview Dialog */}
      <Dialog open={selectedDoc !== null} onOpenChange={() => setSelectedDoc(null)}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>문서 청크 미리보기</DialogTitle>
            <DialogDescription>
              {documents.find((d) => d.id === selectedDoc)?.name} - ChromaDB 인덱싱 청크
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {chunkPreviewData.map((chunk) => (
              <div
                key={chunk.id}
                className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-2"
              >
                <div className="flex items-center justify-between">
                  <Badge variant="secondary" className="bg-sky-100 text-sky-700">
                    Chunk #{chunk.id}
                  </Badge>
                  <div className="flex items-center gap-2 text-xs text-slate-600">
                    <span>Page {chunk.page}</span>
                    <span>•</span>
                    <span>{chunk.tokens} tokens</span>
                  </div>
                </div>
                <p className="text-sm text-slate-700 leading-relaxed">{chunk.content}</p>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
