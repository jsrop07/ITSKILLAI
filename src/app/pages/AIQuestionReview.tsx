import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Textarea } from "../components/ui/textarea";
import {
  FileCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Database,
  FileText,
  Sparkles,
  Edit3,
} from "lucide-react";

const pendingQuestions = [
  {
    id: 1,
    question: "Spring AOP에서 Aspect의 실행 시점을 지정하는 어노테이션은?",
    generatedDate: "2026-04-19 14:23",
    competency: "Spring Framework",
    difficulty: "중급",
    similarityScore: 18,
  },
  {
    id: 2,
    question: "Kafka에서 메시지 순서를 보장하는 방법은?",
    generatedDate: "2026-04-19 13:45",
    competency: "메시징 시스템",
    difficulty: "고급",
    similarityScore: 42,
  },
  {
    id: 3,
    question: "Docker Compose에서 여러 컨테이너 간 네트워크 연결 방법",
    generatedDate: "2026-04-19 12:10",
    competency: "컨테이너 기술",
    difficulty: "중급",
    similarityScore: 15,
  },
];

const selectedQuestionData = {
  id: 1,
  question: "Spring AOP에서 Aspect의 실행 시점을 지정하는 어노테이션은?",
  type: "객관식",
  difficulty: "중급",
  competency: "Spring Framework",
  options: [
    "@Before, @After, @Around",
    "@PreExecute, @PostExecute",
    "@Aspect, @Pointcut",
    "@Component, @Service",
  ],
  correctAnswer: "@Before, @After, @Around",
  explanation:
    "Spring AOP에서는 @Before (메서드 실행 전), @After (메서드 실행 후), @Around (메서드 실행 전후)와 같은 어노테이션을 사용하여 Advice의 실행 시점을 지정합니다. @Around는 가장 강력한 Advice로 메서드 실행을 완전히 제어할 수 있습니다.",
  sourceReferences: [
    "Spring Framework 공식 문서 - AOP Concepts",
    "doc_spring_aop_guide.pdf (p. 12-18)",
    "Spring in Action 5th Edition - Chapter 4",
  ],
  validationResults: {
    grammarCheck: "통과",
    factualAccuracy: "통과",
    difficultyMatch: "일치",
    competencyAlignment: "일치",
  },
  similarQuestions: [
    {
      text: "Spring AOP의 주요 개념인 Aspect, Advice, Pointcut의 차이는?",
      similarity: 35,
    },
    {
      text: "Spring에서 AOP를 구현하는 방법",
      similarity: 28,
    },
  ],
  aiGeneratedAt: "2026-04-19 14:23:15",
  chromadbRetrievals: 8,
  openaiModel: "gpt-4",
};

export default function AIQuestionReview() {
  const [selectedId, setSelectedId] = useState(1);
  const [reviewNote, setReviewNote] = useState("");

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800 flex items-center gap-2">
          <FileCheck className="size-7 text-amber-600" />
          AI 문제 검토
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          AI 생성 문제의 품질 검증 및 승인/거부 처리
        </p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Pending Review List */}
        <Card className="col-span-1 border-slate-200">
          <CardHeader className="border-b border-slate-200">
            <CardTitle className="text-lg">검토 대기 목록</CardTitle>
            <CardDescription>{pendingQuestions.length}개 문제 대기 중</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-slate-100">
              {pendingQuestions.map((q) => (
                <div
                  key={q.id}
                  className={`p-4 cursor-pointer transition-colors ${
                    selectedId === q.id ? "bg-sky-50 border-l-4 border-l-sky-500" : "hover:bg-slate-50"
                  }`}
                  onClick={() => setSelectedId(q.id)}
                >
                  <p className="text-sm font-medium text-slate-800 mb-2">{q.question}</p>
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="secondary" className="bg-sky-100 text-sky-700 text-xs">
                      {q.competency}
                    </Badge>
                    <Badge
                      variant="secondary"
                      className={
                        q.difficulty === "고급"
                          ? "bg-red-100 text-red-700 text-xs"
                          : "bg-amber-100 text-amber-700 text-xs"
                      }
                    >
                      {q.difficulty}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">{q.generatedDate}</span>
                    <Badge
                      variant="secondary"
                      className={
                        q.similarityScore < 20
                          ? "bg-green-100 text-green-700"
                          : q.similarityScore < 40
                          ? "bg-amber-100 text-amber-700"
                          : "bg-red-100 text-red-700"
                      }
                    >
                      유사도 {q.similarityScore}%
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Question Detail & Review */}
        <div className="col-span-2 space-y-6">
          {/* Question Content */}
          <Card className="border-slate-200">
            <CardHeader className="border-b border-slate-200">
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-lg">{selectedQuestionData.question}</CardTitle>
                  <div className="flex items-center gap-2 mt-2">
                    <Badge variant="secondary" className="bg-sky-100 text-sky-700">
                      {selectedQuestionData.competency}
                    </Badge>
                    <Badge variant="secondary" className="bg-amber-100 text-amber-700">
                      {selectedQuestionData.difficulty}
                    </Badge>
                    <Badge variant="secondary" className="bg-violet-100 text-violet-700">
                      <Sparkles className="size-3 mr-1" />
                      AI 생성
                    </Badge>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              {/* Options */}
              <div>
                <p className="text-sm font-medium text-slate-700 mb-3">선택지</p>
                <div className="space-y-2">
                  {selectedQuestionData.options.map((option, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg border text-sm ${
                        option === selectedQuestionData.correctAnswer
                          ? "bg-green-50 border-green-200"
                          : "bg-slate-50 border-slate-200"
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        <span className="font-medium text-slate-600">{idx + 1}.</span>
                        <span className="flex-1 text-slate-700">{option}</span>
                        {option === selectedQuestionData.correctAnswer && (
                          <Badge variant="secondary" className="bg-green-100 text-green-700">
                            정답
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Explanation */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm font-medium text-blue-900 mb-2">해설</p>
                <p className="text-sm text-blue-800 leading-relaxed">
                  {selectedQuestionData.explanation}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Source Grounding & Evidence */}
          <Card className="border-violet-200 bg-gradient-to-br from-violet-50 to-white">
            <CardHeader className="border-b border-violet-100">
              <CardTitle className="text-lg flex items-center gap-2">
                <Database className="size-5 text-violet-600" />
                RAG 출처 검증 및 근거
              </CardTitle>
              <CardDescription>ChromaDB 벡터 검색 기반 문서 참조</CardDescription>
            </CardHeader>
            <CardContent className="pt-4 space-y-3">
              <div>
                <p className="text-sm font-medium text-violet-900 mb-2">참조된 문서</p>
                <div className="space-y-2">
                  {selectedQuestionData.sourceReferences.map((ref, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-3 p-3 bg-white border border-violet-200 rounded-lg"
                    >
                      <FileText className="size-4 text-violet-600 mt-0.5 flex-shrink-0" />
                      <p className="text-sm text-violet-800">{ref}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-violet-200">
                <span className="text-sm text-violet-700">ChromaDB 검색 결과 수</span>
                <Badge variant="secondary" className="bg-violet-100 text-violet-700">
                  {selectedQuestionData.chromadbRetrievals}개 문서
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-violet-700">사용된 LLM 모델</span>
                <Badge variant="secondary" className="bg-violet-100 text-violet-700">
                  {selectedQuestionData.openaiModel}
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Validation Results */}
          <Card className="border-slate-200">
            <CardHeader className="border-b border-slate-200">
              <CardTitle className="text-lg flex items-center gap-2">
                <CheckCircle2 className="size-5 text-green-600" />
                자동 검증 결과
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
              <div className="grid grid-cols-2 gap-4">
                {Object.entries(selectedQuestionData.validationResults).map(([key, value]) => (
                  <div
                    key={key}
                    className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                  >
                    <span className="text-sm text-slate-700">
                      {key === "grammarCheck"
                        ? "문법 검사"
                        : key === "factualAccuracy"
                        ? "사실 정확성"
                        : key === "difficultyMatch"
                        ? "난이도 일치"
                        : "역량 정렬"}
                    </span>
                    <Badge
                      variant="secondary"
                      className={
                        value === "통과" || value === "일치"
                          ? "bg-green-100 text-green-700"
                          : "bg-red-100 text-red-700"
                      }
                    >
                      <CheckCircle2 className="size-3 mr-1" />
                      {value}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Similarity Warning */}
          <Card className="border-amber-200 bg-amber-50">
            <CardHeader className="border-b border-amber-200">
              <CardTitle className="text-lg flex items-center gap-2">
                <AlertTriangle className="size-5 text-amber-600" />
                유사 문제 경고
              </CardTitle>
              <CardDescription>기존 문제와의 유사도 분석</CardDescription>
            </CardHeader>
            <CardContent className="pt-4 space-y-3">
              {selectedQuestionData.similarQuestions.map((sq, idx) => (
                <div
                  key={idx}
                  className="flex items-start justify-between p-3 bg-white border border-amber-200 rounded-lg"
                >
                  <p className="text-sm text-slate-700 flex-1">{sq.text}</p>
                  <Badge
                    variant="secondary"
                    className={
                      sq.similarity < 30
                        ? "bg-green-100 text-green-700"
                        : sq.similarity < 50
                        ? "bg-amber-100 text-amber-700"
                        : "bg-red-100 text-red-700"
                    }
                  >
                    {sq.similarity}%
                  </Badge>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Review Notes */}
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Edit3 className="size-5 text-slate-600" />
                검토 의견
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                placeholder="검토 의견을 입력하세요 (선택 사항)"
                value={reviewNote}
                onChange={(e) => setReviewNote(e.target.value)}
                rows={4}
                className="resize-none"
              />
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex items-center gap-4">
            <Button className="flex-1 bg-green-600 hover:bg-green-700 h-12">
              <CheckCircle2 className="size-5 mr-2" />
              승인 및 문제 은행에 추가
            </Button>
            <Button variant="outline" className="flex-1 h-12">
              <Edit3 className="size-5 mr-2" />
              수정 후 승인
            </Button>
            <Button variant="outline" className="flex-1 text-red-600 hover:text-red-700 h-12">
              <XCircle className="size-5 mr-2" />
              거부
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
