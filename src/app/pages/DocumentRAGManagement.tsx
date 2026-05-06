import { useEffect, useState } from "react";
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
import {
  aiDocumentApi,
  AIDocument,
  RAGSearchResult,
  RAGSearchMode,
} from "../../lib/api";
import {
  COMPETENCY_OPTIONS,
  TOPIC_PLACEHOLDER_MAP,
  getCompetencyLabel,
} from "../../lib/types";

export default function DocumentRAGManagement() {
  const [documents, setDocuments] = useState<AIDocument[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [retrievalResults, setRetrievalResults] = useState<RAGSearchResult[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<AIDocument | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [isSearching, setIsSearching] = useState(false);

  const [uploadOpen, setUploadOpen] = useState(false);
  const [generateOpen, setGenerateOpen] = useState(false);

  const [title, setTitle] = useState("");
  const [sourceType, setSourceType] = useState("NCS");
  const [category, setCategory] = useState("");
  const [searchCategory, setSearchCategory] = useState("");
  const [searchMode, setSearchMode] = useState<"vector" | "keyword" | "hybrid">("hybrid");
  const [generateCategory, setGenerateCategory] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState<"초급" | "중급" | "고급">("초급");
  const [count, setCount] = useState(1);
  const [topK, setTopK] = useState(3);

  // topicPlaceholderMap, competencyOptions는 ../../lib/types의 공통 상수(TOPIC_PLACEHOLDER_MAP, COMPETENCY_OPTIONS)로 통합됨


  const loadDocuments = async () => {
    try {
      const data = await aiDocumentApi.list();
      setDocuments(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("문서 목록 조회 실패:", error);
      setDocuments([]);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const getStatusText = (status?: string) => {
    switch (status) {
      case "completed":
        return "인덱싱 완료";
      case "processing":
        return "인덱싱 중";
      case "failed":
        return "인덱싱 실패";
      case "pending":
      default:
        return "인덱싱 대기";
    }
  };

  const getStatusClassName = (status?: string) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-700";
      case "processing":
        return "bg-blue-100 text-blue-700";
      case "failed":
        return "bg-red-100 text-red-700";
      case "pending":
      default:
        return "bg-slate-100 text-slate-700";
    }
  };

  const handleUpload = async () => {
    if (!title.trim()) {
      alert("문서 제목을 입력해주세요.");
      return;
    }
    if (!category) {
      alert("문서 카테고리를 선택해주세요.");
      return;
    }

    if (!file) {
      alert("업로드할 파일을 선택해주세요.");
      return;
    }

    const formData = new FormData();
    formData.append("title", title);
    formData.append("source_type", sourceType);
    formData.append("category", category);
    formData.append("description", description);
    formData.append("file", file);

    try {
      setIsLoading(true);
      await aiDocumentApi.upload(formData);
      alert("문서 업로드가 완료되었습니다.");

      setTitle("");
      setSourceType("NCS");
      setCategory("");
      setDescription("");
      setFile(null);
      setUploadOpen(false);

      await loadDocuments();
    } catch (error: any) {
      alert(error.response?.data?.detail || "문서 업로드 중 오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmbed = async (documentId: number) => {
    try {
      setIsLoading(true);
      await aiDocumentApi.embed(documentId);
      alert("문서 인덱싱이 완료되었습니다.");
      await loadDocuments();
    } catch (error: any) {
      alert(error.response?.data?.detail || "문서 인덱싱 중 오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetrievalTest = async () => {
    if (!searchQuery.trim()) {
      alert("검색 쿼리를 입력해주세요.");
      return;
    }

    try {
      setIsSearching(true);

      const res = await aiDocumentApi.search({
        query: searchQuery,
        top_k: topK,
        category: searchCategory || undefined,
        search_mode: searchMode,
      });

      setRetrievalResults(res.results || []);
    } catch (error: any) {
      console.error(error);
      alert(error.response?.data?.detail || "문서 검색 중 오류가 발생했습니다.");
    } finally {
      setIsSearching(false);
    }
  };

  const handleGenerateQuestions = async () => {
    if (!topic.trim()) {
      alert("문제 생성 주제를 입력해주세요.");
      return;
    }

    if (!generateCategory) {
      alert("문제 생성에 사용할 역량 유형을 선택해주세요.");
      return;
    }

    const categoryLabel =
      COMPETENCY_OPTIONS.find((item) => item.value === generateCategory)?.label || "";

    try {
      setIsLoading(true);

      const res = await aiDocumentApi.generateQuestions({
        topic,
        difficulty,
        count,
        question_type: "multiple_choice",
        competency_type: generateCategory,
        search_query: `${categoryLabel} ${topic}`,
        top_k: topK,
      });

      console.log("문서 기반 문제 생성 결과:", res);
      alert("문서 기반 문제가 생성되었습니다.");
      setGenerateOpen(false);
    } catch (error: any) {
      alert(error.response?.data?.detail || "문제 생성 중 오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  const completedDocuments = (documents ?? []).filter(
    (doc) => doc.embedding_status === "completed"
  );

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

        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setGenerateOpen(true)}
            disabled={completedDocuments.length === 0}
          >
            <Sparkles className="size-4 mr-2" />
            문서 기반 문제 생성
          </Button>

          <Button
            className="bg-sky-600 hover:bg-sky-700"
            onClick={() => setUploadOpen(true)}
          >
            <Upload className="size-4 mr-2" />
            문서 업로드
          </Button>
        </div>
      </div>

      <Card className="border-violet-200 bg-gradient-to-r from-violet-50 to-sky-50">
        <CardContent className="py-4">
          <div className="flex items-center gap-4">
            <div className="size-12 rounded-full bg-violet-100 flex items-center justify-center">
              <Database className="size-6 text-violet-600" />
            </div>

            <div className="flex-1">
              <h3 className="text-sm font-semibold text-slate-800">
                ChromaDB 벡터 데이터베이스
              </h3>
              <p className="text-sm text-slate-600 mt-0.5">
                OpenAI Embeddings를 활용한 RAG 검색 엔진
              </p>
            </div>

            <div className="text-right">
              <p className="text-2xl font-bold text-violet-700">
                {completedDocuments.length}
              </p>
              <p className="text-xs text-slate-600">인덱싱 완료 문서</p>
            </div>

            <div className="text-right">
              <p className="text-2xl font-bold text-sky-700">{documents.length}</p>
              <p className="text-xs text-slate-600">전체 문서</p>
            </div>
          </div>
        </CardContent>
      </Card>

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
                <TableHead>출처</TableHead>
                <TableHead>카테고리</TableHead>
                <TableHead>업로드일</TableHead>
                <TableHead>인덱싱 상태</TableHead>
                <TableHead className="text-right">작업</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {documents.map((doc) => (
                <TableRow key={doc.document_id}>
                  <TableCell className="font-medium flex items-center gap-2">
                    <FileText className="size-4 text-slate-400" />
                    {doc.title}
                  </TableCell>

                  <TableCell>
                    <Badge variant="secondary" className="bg-blue-100 text-blue-700">
                      {doc.source_type || "-"}
                    </Badge>
                  </TableCell>

                  <TableCell>
                    <Badge variant="secondary" className="bg-sky-100 text-sky-700">
                      {getCompetencyLabel(doc.category)}
                    </Badge>
                  </TableCell>

                  <TableCell className="text-slate-500 text-sm">
                    {doc.created_at
                      ? new Date(doc.created_at).toLocaleString()
                      : "-"}
                  </TableCell>

                  <TableCell>
                    <Badge
                      variant="secondary"
                      className={getStatusClassName(doc.embedding_status)}
                    >
                      {doc.embedding_status === "completed" && (
                        <CheckCircle2 className="size-3 mr-1" />
                      )}
                      {doc.embedding_status === "processing" && (
                        <Clock className="size-3 mr-1" />
                      )}
                      {doc.embedding_status === "failed" && (
                        <AlertCircle className="size-3 mr-1" />
                      )}
                      {getStatusText(doc.embedding_status)}
                    </Badge>

                    {doc.embedding_error && (
                      <p className="mt-1 text-xs text-red-500">
                        {doc.embedding_error}
                      </p>
                    )}
                  </TableCell>

                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedDoc(doc)}
                      >
                        정보 보기
                      </Button>

                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={
                          isLoading ||
                          doc.embedding_status === "completed" ||
                          doc.embedding_status === "processing"
                        }
                        onClick={() => handleEmbed(doc.document_id)}
                      >
                        <RefreshCw className="size-4 mr-2" />
                        인덱싱
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}

              {documents.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="py-8 text-center text-slate-500">
                    업로드된 문서가 없습니다.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

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
              <label className="text-sm font-medium text-slate-700">
                검색 대상 역량 유형
              </label>
              <select
                value={searchCategory}
                onChange={(e) => setSearchCategory(e.target.value)}
                className="w-full h-10 rounded-md border border-slate-200 bg-white px-3 text-sm"
              >
                <option value="">전체 문서</option>
                {COMPETENCY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">
                검색 모드
              </label>
              <select
                value={searchMode}
                onChange={(e) => setSearchMode(e.target.value as RAGSearchMode)}
                className="w-full h-10 rounded-md border border-slate-200 bg-white px-3 text-sm"
              >
                <option value="vector">Vector Search</option>
                <option value="keyword">Keyword Search</option>
                <option value="hybrid">Hybrid Search</option>
              </select>
            </div>
          </CardContent>
          <CardContent className="pt-6 space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">
                검색 쿼리
              </label>
              <Textarea
                placeholder="예: Java 상속과 오버라이딩"
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
                  {searchMode === "vector" && "벡터 검색 실행"}
                  {searchMode === "keyword" && "키워드 검색 실행"}
                  {searchMode === "hybrid" && "하이브리드 검색 실행"}
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
                    key={`${result.metadata?.chunk_id ?? idx}-${idx}`}
                    className="p-3 bg-gradient-to-r from-violet-50 to-sky-50 border border-violet-200 rounded-lg"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <Badge variant="secondary" className="bg-violet-100 text-violet-700">
                        Chunk #{result.metadata?.chunk_index ?? idx}
                      </Badge>

                      <Badge variant="secondary" className="bg-sky-100 text-sky-700">
                        {result.search_source || searchMode}
                      </Badge>
                    </div>

                    <div className="flex flex-wrap gap-2 mb-2">
                      <Badge variant="secondary" className="bg-slate-100 text-slate-700">
                        vector{" "}
                        {typeof result.vector_score === "number"
                          ? result.vector_score.toFixed(3)
                          : typeof result.similarity === "number"
                            ? result.similarity.toFixed(3)
                            : "-"}
                      </Badge>

                      <Badge variant="secondary" className="bg-slate-100 text-slate-700">
                        keyword{" "}
                        {typeof result.keyword_score === "number"
                          ? result.keyword_score.toFixed(3)
                          : "-"}
                      </Badge>

                      <Badge variant="secondary" className="bg-slate-100 text-slate-700">
                        hybrid{" "}
                        {typeof result.hybrid_score === "number"
                          ? result.hybrid_score.toFixed(3)
                          : "-"}
                      </Badge>

                      <Badge variant="secondary" className="bg-slate-100 text-slate-700">
                        similarity{" "}
                        {typeof result.similarity === "number"
                          ? result.similarity.toFixed(3)
                          : "-"}
                      </Badge>
                    </div>

                    <p className="text-xs text-slate-500 mb-2">
                      {result.metadata?.title || result.metadata?.file_name || "문서 정보 없음"}
                      {" · "}
                      {result.metadata?.category || "-"}
                    </p>

                    <p className="text-sm text-slate-700 leading-relaxed">
                      {result.content}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Database className="size-12 text-slate-300 mx-auto mb-3" />
                <p className="text-sm text-slate-500">
                  검색 쿼리를 입력하고 검색 모드를 선택한 뒤 검색을 실행하세요
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>문서 업로드</DialogTitle>
            <DialogDescription>
              PDF, DOCX, TXT, MD 문서를 업로드하면 chunk로 분리되어 저장됩니다.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <Input
              placeholder="문서 제목"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />

            <Input
              placeholder="출처 타입 예: NCS"
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value)}
            />

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">
                문서 카테고리
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full h-10 rounded-md border border-slate-200 bg-white px-3 text-sm"
              >
                <option value="">카테고리 선택</option>
                {COMPETENCY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <Textarea
              placeholder="설명"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />

            <Input
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />

            <Button
              className="w-full bg-sky-600 hover:bg-sky-700"
              disabled={isLoading}
              onClick={handleUpload}
            >
              업로드
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={generateOpen} onOpenChange={setGenerateOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>문서 기반 문제 생성</DialogTitle>
            <DialogDescription>
              인덱싱 완료된 문서를 검색해 관련 내용을 기반으로 문제를 생성합니다.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">
                문제 생성 역량 유형
              </label>
              <select
                value={generateCategory}
                onChange={(e) => setGenerateCategory(e.target.value)}
                className="w-full h-10 rounded-md border border-slate-200 bg-white px-3 text-sm"
              >
                <option value="">역량 유형 선택</option>
                {COMPETENCY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <Input
              placeholder={TOPIC_PLACEHOLDER_MAP[generateCategory] || "예: 평가할 IT 세부 주제를 입력하세요"}
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
            />

            <select
              className="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"
              value={difficulty}
              onChange={(e) =>
                setDifficulty(e.target.value as "초급" | "중급" | "고급")
              }
            >
              <option value="초급">초급</option>
              <option value="중급">중급</option>
              <option value="고급">고급</option>
            </select>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">생성 문제 수</label>
              <select
                className="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
              >
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                  <option key={num} value={num}>
                    {num}문제
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">참고 Chunk 수 (Top-K)</label>
              <select
                className="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
              >
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                  <option key={num} value={num}>
                    {num}개
                  </option>
                ))}
              </select>
            </div>

            <Button
              className="w-full bg-indigo-600 hover:bg-indigo-700"
              disabled={isLoading}
              onClick={handleGenerateQuestions}
            >
              문제 생성
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={selectedDoc !== null} onOpenChange={() => setSelectedDoc(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>문서 정보</DialogTitle>
            <DialogDescription>{selectedDoc?.title}</DialogDescription>
          </DialogHeader>

          {selectedDoc && (
            <div className="space-y-2 text-sm text-slate-700">
              <p>파일명: {selectedDoc.file_name}</p>
              <p>출처: {selectedDoc.source_type || "-"}</p>
              <p>카테고리: {getCompetencyLabel(selectedDoc.category)}</p>
              <p>설명: {selectedDoc.description || "-"}</p>
              <p>상태: {getStatusText(selectedDoc.embedding_status)}</p>
              {selectedDoc.embedding_error && (
                <p className="text-red-500">오류: {selectedDoc.embedding_error}</p>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}