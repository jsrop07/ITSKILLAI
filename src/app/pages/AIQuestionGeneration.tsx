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

const roleOptions = [
  { value: "backend", label: "백엔드 개발자" },
  { value: "frontend", label: "프론트엔드 개발자" },
  { value: "fullstack", label: "풀스택 개발자" },
  { value: "python", label: "Python 개발자" },
  { value: "java", label: "Java 개발자" },
  { value: "ai_developer", label: "인공지능 개발자" },
  { value: "ml_engineer", label: "머신러닝 엔지니어" },
  { value: "data_analyst", label: "데이터 분석가" },
  { value: "data_engineer", label: "데이터 엔지니어" },
  { value: "cloud_devops", label: "클라우드/DevOps 엔지니어" },
  { value: "security", label: "정보보안 엔지니어" },
  { value: "dba", label: "DBA/데이터베이스 엔지니어" },
  { value: "junior_common", label: "신입 개발자 공통" },
];

const competencyOptions = [
  { value: "programming_language", label: "프로그래밍 언어" },
  { value: "data_structure_algorithm", label: "자료구조/알고리즘" },
  { value: "web_backend", label: "웹/백엔드 개발" },
  { value: "frontend", label: "프론트엔드 개발" },
  { value: "database", label: "데이터베이스" },
  { value: "operating_system", label: "운영체제" },
  { value: "network", label: "네트워크" },
  { value: "security", label: "정보보안" },
  { value: "cloud_devops", label: "클라우드/DevOps" },
  { value: "ai_ml", label: "인공지능/머신러닝" },
  { value: "data_analysis", label: "데이터 분석" },
  { value: "software_engineering", label: "소프트웨어공학" },
  { value: "ncs_application_sw", label: "NCS 응용SW개발" },
  { value: "ncs_database", label: "NCS 데이터베이스" },
  { value: "ncs_security", label: "NCS 정보보안" },
];

const difficultyOptions = [
  { value: "초급", label: "초급" },
  { value: "중급", label: "중급" },
  { value: "고급", label: "고급" },
];

const questionTypeOptions = [
  { value: "multiple_choice", label: "객관식" },
  { value: "essay", label: "서술형" },
  { value: "coding", label: "코드작성형" },
];

const documentScopeOptions = [
  { value: "none", label: "문서 사용 안 함" },
  { value: "rag_all", label: "전체 인덱싱 문서 기반 생성" },
];

type QuestionTypeValue = "multiple_choice" | "essay" | "coding";
type DifficultyValue = "초급" | "중급" | "고급";
type DocumentScopeValue = "none" | "rag_all";

export default function AIQuestionGeneration() {
  const [role, setRole] = useState("backend");
  const [competencyType, setCompetencyType] = useState("programming_language");
  const [difficulty, setDifficulty] = useState<"초급" | "중급" | "고급">("초급");
  const [questionType, setQuestionType] = useState<"multiple_choice" | "essay" | "coding">("multiple_choice");
  const [documentScope, setDocumentScope] = useState<"none" | "rag_all">("none");
  const [detailedTopic, setDetailedTopic] = useState("");
  const [count, setCount] = useState(5);
  const [topK, setTopK] = useState(5);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedQuestions, setGeneratedQuestions] = useState<any[]>([]);

  const handleGenerate = async () => {
    if (!detailedTopic.trim()) {
      alert("세부 주제를 입력해주세요.");
      return;
    }

    const selectedRole = roleOptions.find((item) => item.value === role);
    const selectedCompetency = competencyOptions.find(
      (item) => item.value === competencyType
    );

    const searchQuery = [
      selectedRole?.label,
      selectedCompetency?.label,
      detailedTopic,
    ]
      .filter(Boolean)
      .join(" ");

    const payload = {
      topic: detailedTopic,
      difficulty,
      count,
      question_type: questionType,
      role,
      competency_type: competencyType,
      search_query: searchQuery,
      top_k: topK,
    };

    try {
      setIsGenerating(true);

      const result =
        documentScope === "rag_all"
          ? await aiQuestionApi.generateFromDocument(payload)
          : await aiQuestionApi.generateGeneral(payload);

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
          OpenAI LLM과 ChromaDB RAG를 활용한 지능형 문제 생성
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
          <CardContent className="pt-6 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="role">대상 직무 *</Label>
              <Select value={role} onValueChange={setRole}>
                <SelectTrigger id="role">
                  <SelectValue placeholder="대상 직무 선택" />
                </SelectTrigger>
                <SelectContent>
                  {roleOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="competency">역량 유형 *</Label>
              <Select value={competencyType} onValueChange={setCompetencyType}>
                <SelectTrigger>
                  <SelectValue placeholder="역량 유형 선택" />
                </SelectTrigger>
                <SelectContent>
                  {competencyOptions.map((option) => (
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
                placeholder="예: 트랜잭션 전파 옵션, N+1 쿼리 최적화, CSRF 보안"
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
              <Input
                id="count"
                type="number"
                min="1"
                max="20"
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
              />
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
                          <Badge variant="secondary" className="bg-sky-100 text-sky-700">
                            {q.question_type || questionType}
                          </Badge>
                          <Badge variant="secondary" className="bg-green-100 text-green-700">
                            {q.difficulty || difficulty}
                          </Badge>
                          <Badge variant="secondary" className="bg-violet-100 text-violet-700">
                            {q.review_status || "pending"}
                          </Badge>
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
