import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Badge } from "../components/ui/badge";
import { Sparkles, RotateCw } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { aiQuestionApi } from "../../lib/api";
import {
  COMPETENCY_OPTIONS,
  TOPIC_PLACEHOLDER_MAP,
  AI_GENERATION_TYPE_LABELS,
  type CompetencyTypeValue,
} from "../../lib/types";
const formatDate = (dateStr?: string) => {
  if (!dateStr) return "-";
  try {
    const d = new Date(dateStr);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  } catch {
    return "-";
  }
};

const getGenerationBadgeClass = (type?: string | null) => {
  switch (type) {
    case "rag":
      return "bg-indigo-100 text-indigo-700 border-indigo-200";
    case "general":
      return "bg-cyan-100 text-cyan-700 border-cyan-200";
    case "manual":
      return "bg-slate-100 text-slate-700 border-slate-200";
    default:
      return "bg-amber-100 text-amber-700 border-amber-200";
  }
};

const typeColor: Record<string, string> = {
  multiple_choice: "bg-blue-100 text-blue-700 border-blue-200",
  essay: "bg-emerald-100 text-emerald-700 border-emerald-200",
  coding: "bg-orange-100 text-orange-700 border-orange-200",
};

const difficultyColor: Record<string, string> = {
  초급: "bg-green-100 text-green-700 border-green-200",
  중급: "bg-amber-100 text-amber-700 border-amber-200",
  고급: "bg-red-100 text-red-700 border-red-200",
};

const difficultyOptions = [
  { value: "초급", label: "초급" },
  { value: "중급", label: "중급" },
  { value: "고급", label: "고급" },
];

const QUESTION_TYPE_LABELS: Record<string, string> = {
  multiple_choice: "객관식",
  essay: "서술형",
  coding: "코드작성형",
};

const questionTypeOptions = [
  { value: "multiple_choice", label: "객관식" },
  { value: "essay", label: "서술형" },
  { value: "coding", label: "코드작성형" },
];

const documentScopeOptions = [
  { value: "none", label: "문서 사용 안 함" },
  { value: "rag_all", label: "전체 인덱싱 문서 기반 생성" },
];

const searchModeOptions = [
  { value: "hybrid", label: "Hybrid 검색 (Vector + FULLTEXT + RRF)" },
  { value: "vector", label: "Vector 검색 (ChromaDB)" },
  { value: "keyword", label: "Keyword 검색 (MariaDB FULLTEXT)" },
];

type QuestionTypeValue = "multiple_choice" | "essay" | "coding";
type DifficultyValue = "초급" | "중급" | "고급";
type DocumentScopeValue = "none" | "rag_all";

export default function AIQuestionGeneration() {
  // const [role, setRole] = useState("backend");
  const [competencyType, setCompetencyType] =
    useState<CompetencyTypeValue>("software_engineering");
  const [difficulty, setDifficulty] = useState<"초급" | "중급" | "고급">("초급");
  const [questionType, setQuestionType] = useState<"multiple_choice" | "essay" | "coding">("multiple_choice");
  const [documentScope, setDocumentScope] = useState<"none" | "rag_all">("none");
  const [detailedTopic, setDetailedTopic] = useState("");
  const [count, setCount] = useState(5);
  const [topK, setTopK] = useState(5);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedQuestions, setGeneratedQuestions] = useState<any[]>([]);
  const [searchMode, setSearchMode] = useState<"vector" | "keyword" | "hybrid">("hybrid");
  const isRagEnabled = documentScope === "rag_all";

  const handleGenerate = async () => {
    if (!competencyType) {
      alert("역량 유형을 선택해주세요.");
      return;
    }
    if (!detailedTopic.trim()) {
      alert("세부 주제를 입력해주세요.");
      return;
    }

    const blockedNonItKeywords = [
      "음식",
      "맛집",
      "요리",
      "레시피",
      "여행",
      "연애",
      "소개팅",
      "운세",
      "영화",
      "노래",
      "쇼핑",
    ];

    const hasBlockedKeyword = blockedNonItKeywords.some((keyword) =>
      detailedTopic.toLowerCase().includes(keyword.toLowerCase())
    );

    if (hasBlockedKeyword) {
      alert("세부 주제는 IT 역량진단과 관련된 주제만 입력할 수 있습니다.");
      return;
    }
    const selectedCompetency = COMPETENCY_OPTIONS.find(
      (item) => item.value === competencyType
    );

    const searchQuery = [
      // selectedRole?.label,
      selectedCompetency?.label,
      detailedTopic,
    ]
      .filter(Boolean)
      .join(" ");

    const basePayload = {
      topic: detailedTopic,
      difficulty,
      count,
      question_type: questionType,
      competency_type: competencyType,
    };

    const generalPayload = {
      ...basePayload,
    };

    const ragPayload = {
      ...basePayload,
      search_query: searchQuery,
      top_k: topK,
      search_mode: searchMode,
    };

    try {
      setIsGenerating(true);

      const result = isRagEnabled
        ? await aiQuestionApi.generateFromDocument(ragPayload)
        : await aiQuestionApi.generateGeneral(generalPayload);

      console.log("AI 문제 생성 결과:", result);

      const savedQuestions = result.data || result.questions || [];
      setGeneratedQuestions(savedQuestions);

      alert("AI 문제가 생성되었습니다. 검수 화면에서 확인해주세요.");
    } catch (error: any) {
      console.error("AI 문제 생성 실패:", error);
      console.error("백엔드 응답:", error.response?.data);

      alert(
        error.response?.data?.detail ||
        "AI 문제 생성 중 오류가 발생했습니다. 백엔드 터미널 로그를 확인해주세요."
      );
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800 flex items-center gap-2">
          <Sparkles className="size-7 text-violet-600" />
          AI 문제 생성
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          OpenAI LLM + Hybrid RAG 기반 지능형 문제 생성
        </p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Generation Form */}
        <Card className="col-span-1 border-sky-200 bg-gradient-to-br from-white to-sky-50/30">
          <CardHeader className="border-b border-sky-100">
            <CardTitle className="text-lg flex items-center gap-2">
              <Sparkles className="size-5 text-sky-600" />
              생성 설정
            </CardTitle>
            <CardDescription>문제 생성을 위한 파라미터 설정</CardDescription>
          </CardHeader>
          <CardContent className="pt-1 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="competency">역량 유형 *</Label>
              <Select
                value={competencyType}
                onValueChange={(value) => setCompetencyType(value as CompetencyTypeValue)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="역량 유형 선택" />
                </SelectTrigger>
                <SelectContent>
                  {COMPETENCY_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="topic">세부 주제 *</Label>
              <Textarea
                id="topic"
                placeholder={TOPIC_PLACEHOLDER_MAP[competencyType] || "예: 평가할 IT 세부 주제를 입력하세요"}
                value={detailedTopic}
                onChange={(e) => setDetailedTopic(e.target.value)}
                rows={3}
                className="resize-none"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="type">문제 유형 *</Label>
              <Select
                value={questionType}
                onValueChange={(value) => setQuestionType(value as QuestionTypeValue)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="문제 유형 선택" />
                </SelectTrigger>
                <SelectContent>
                  {questionTypeOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="count">생성 문제 수 *</Label>
              <Select
                value={String(count)}
                onValueChange={(value) => setCount(Number(value))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="문제 수 선택" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1문제</SelectItem>
                  <SelectItem value="2">2문제</SelectItem>
                  <SelectItem value="3">3문제</SelectItem>
                  <SelectItem value="4">4문제</SelectItem>
                  <SelectItem value="5">5문제</SelectItem>
                  <SelectItem value="6">6문제</SelectItem>
                  <SelectItem value="7">7문제</SelectItem>
                  <SelectItem value="8">8문제</SelectItem>
                  <SelectItem value="9">9문제</SelectItem>
                  <SelectItem value="10">10문제</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="difficulty">난이도 *</Label>
              <Select
                value={difficulty}
                onValueChange={(value) => setDifficulty(value as DifficultyValue)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="난이도 선택" />
                </SelectTrigger>
                <SelectContent>
                  {difficultyOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="scope">문서 범위 (RAG)</Label>
              <Select
                value={documentScope}
                onValueChange={(value) => setDocumentScope(value as DocumentScopeValue)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="문서 범위 선택" />
                </SelectTrigger>
                <SelectContent>
                  {documentScopeOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {isRagEnabled && (
              <div className="space-y-2">
                <Label htmlFor="searchMode">검색 방식(RAG)</Label>
                <Select
                  value={searchMode}
                  onValueChange={(value) =>
                    setSearchMode(value as "vector" | "keyword" | "hybrid")
                  }
                >
                  <SelectTrigger id="searchMode">
                    <SelectValue placeholder="검색 방식 선택" />
                  </SelectTrigger>
                  <SelectContent>
                    {searchModeOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <Button
              className="w-full bg-gradient-to-r from-violet-600 to-sky-600 hover:from-violet-700 hover:to-sky-700 mt-6"
              onClick={handleGenerate}
              disabled={isGenerating}
            >
              {isGenerating ? (
                <>
                  <RotateCw className="size-4 mr-2 animate-spin" />
                  AI 문제 생성 중...
                </>
              ) : (
                <>
                  <Sparkles className="size-4 mr-2" />
                  AI 문제 생성
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Generated Questions */}
        <div className="col-span-2 space-y-6">
          {generatedQuestions.length > 0 ? (
            <>
              <Card className="border-violet-200 bg-gradient-to-br from-violet-50 to-white">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Sparkles className="size-5 text-violet-600" />
                    생성 결과 요약
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold text-violet-700">
                    {generatedQuestions.length}
                  </p>
                  <p className="text-sm text-slate-600 mt-1">생성된 문제</p>
                </CardContent>
              </Card>

              {generatedQuestions.map((q, index) => (
                <Card key={q.id ?? index} className="border-slate-200">
                  <CardHeader className="border-b border-slate-100">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <CardTitle className="text-base font-medium text-slate-800">
                          {q.body || q.question || "문제 내용 없음"}
                        </CardTitle>

                        <div className="flex items-center gap-2 mt-2">
                          <Badge variant="secondary" className={typeColor[q.question_type || questionType] || "bg-slate-100 text-slate-700"}>
                            {QUESTION_TYPE_LABELS[q.question_type || questionType] || q.question_type || questionType}
                          </Badge>
                          <Badge variant="secondary" className={difficultyColor[q.difficulty || difficulty] || "bg-slate-100 text-slate-700"}>
                            {q.difficulty || difficulty}
                          </Badge>
                          <Badge variant="secondary" className="bg-slate-100 text-slate-700">
                            {q.review_status || "pending"}
                          </Badge>
                          <Badge variant="outline" className={`${getGenerationBadgeClass(q.ai_generation_type || (documentScope === "rag_all" ? "rag" : "general"))} font-medium border`}>
                            {q.ai_generation_type ? AI_GENERATION_TYPE_LABELS[q.ai_generation_type] : (documentScope === "rag_all" ? "문서 기반 RAG" : "설계서 기반")}
                          </Badge>
                          <span className="text-sm text-slate-600 font-medium ml-auto">
                            {formatDate(q.created_at)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </CardHeader>

                  <CardContent className="pt-4 space-y-4">
                    {Array.isArray(q.choices) && q.choices.length > 0 && (
                      <div className="space-y-2">
                        <p className="text-sm font-medium text-slate-700">선택지</p>
                        {q.choices.map((choice: string, idx: number) => (
                          <div
                            key={idx}
                            className="p-3 rounded-lg border text-sm bg-slate-50 border-slate-200"
                          >
                            <span className="font-medium text-slate-600">
                              {idx + 1}.
                            </span>{" "}
                            <span className="text-slate-700">{choice}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                      <p className="text-sm font-medium text-blue-900 mb-1">
                        정답 / 모범답안
                      </p>
                      <p className="text-sm text-blue-800 leading-relaxed">
                        {typeof q.answer === "object"
                          ? JSON.stringify(q.answer)
                          : q.answer || "-"}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </>
          ) : (
            <Card className="border-slate-200">
              <CardContent className="py-16 text-center">
                <Sparkles className="size-16 text-slate-300 mx-auto mb-4" />
                <p className="text-lg font-medium text-slate-700">
                  AI 문제 생성 대기 중
                </p>
                <p className="text-sm text-slate-500 mt-2">
                  좌측 설정 폼을 작성하고 'AI 문제 생성' 버튼을 클릭하세요
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
