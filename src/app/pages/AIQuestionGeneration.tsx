import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Badge } from "../components/ui/badge";
import { Sparkles, CheckCircle2, XCircle, RotateCw, Save, Database, FileText } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";

const mockGeneratedQuestions = [
  {
    id: 1,
    question: "Spring Boot에서 @Transactional 애노테이션의 전파(Propagation) 옵션 중 REQUIRES_NEW의 동작 방식은?",
    options: [
      "기존 트랜잭션이 있으면 참여하고, 없으면 새로 생성",
      "항상 새로운 트랜잭션을 생성하고, 기존 트랜잭션은 일시 중단",
      "기존 트랜잭션이 있어야만 실행 가능",
      "트랜잭션 없이 실행",
    ],
    correctAnswer: "항상 새로운 트랜잭션을 생성하고, 기존 트랜잭션은 일시 중단",
    explanation: "REQUIRES_NEW는 항상 새로운 트랜잭션을 시작하며, 기존 트랜잭션이 있는 경우 이를 일시 중단합니다. 이는 독립적인 트랜잭션 처리가 필요한 경우 유용합니다.",
    competencyTags: ["Spring Framework", "트랜잭션 관리", "어노테이션"],
    difficulty: "고급",
    sourceReferences: [
      "Spring Framework 공식 문서 - Transaction Propagation",
      "doc_spring_transaction_guide.pdf (p. 24-27)",
    ],
    validationStatus: "검증됨",
    similarity: 12,
  },
  {
    id: 2,
    question: "JPA에서 영속성 컨텍스트의 1차 캐시가 제공하는 이점은?",
    options: [
      "데이터베이스 접근 횟수 감소 및 동일성 보장",
      "분산 환경에서의 캐시 공유",
      "영구적인 데이터 저장",
      "자동 인덱스 생성",
    ],
    correctAnswer: "데이터베이스 접근 횟수 감소 및 동일성 보장",
    explanation: "1차 캐시는 영속성 컨텍스트 내에서 엔티티를 저장하여 동일한 엔티티에 대한 반복적인 데이터베이스 조회를 방지하고, 같은 식별자를 가진 엔티티에 대해 동일성(==)을 보장합니다.",
    competencyTags: ["JPA", "영속성 컨텍스트", "캐싱"],
    difficulty: "중급",
    sourceReferences: [
      "JPA 프로그래밍 가이드 - 영속성 관리",
      "doc_jpa_persistence_context.pdf (p. 15-18)",
    ],
    validationStatus: "검증됨",
    similarity: 8,
  },
  {
    id: 3,
    question: "Spring Security에서 CSRF 토큰의 주요 목적은?",
    options: [
      "사용자 인증 정보 저장",
      "크로스 사이트 요청 위조 공격 방지",
      "세션 관리 및 타임아웃 처리",
      "암호화된 통신 보장",
    ],
    correctAnswer: "크로스 사이트 요청 위조 공격 방지",
    explanation: "CSRF 토큰은 악의적인 웹사이트가 사용자의 인증된 세션을 이용하여 의도하지 않은 요청을 보내는 것을 방지합니다. 서버는 각 요청에 포함된 토큰을 검증하여 요청의 정당성을 확인합니다.",
    competencyTags: ["Spring Security", "보안", "CSRF"],
    difficulty: "중급",
    sourceReferences: [
      "Spring Security 레퍼런스 - CSRF Protection",
      "doc_web_security_best_practices.pdf (p. 42-45)",
    ],
    validationStatus: "검증됨",
    similarity: 15,
  },
];

export default function AIQuestionGeneration() {
  const [role, setRole] = useState("");
  const [level, setLevel] = useState("");
  const [competency, setCompetency] = useState("");
  const [detailedTopic, setDetailedTopic] = useState("");
  const [questionType, setQuestionType] = useState("");
  const [questionCount, setQuestionCount] = useState("5");
  const [difficulty, setDifficulty] = useState("");
  const [documentScope, setDocumentScope] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedQuestions, setGeneratedQuestions] = useState<typeof mockGeneratedQuestions>([]);

  const handleGenerate = () => {
    setIsGenerating(true);
    // Simulate AI generation
    setTimeout(() => {
      setGeneratedQuestions(mockGeneratedQuestions);
      setIsGenerating(false);
    }, 2000);
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
                  <SelectValue placeholder="직무 선택" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="backend">백엔드 개발자</SelectItem>
                  <SelectItem value="frontend">프론트엔드 개발자</SelectItem>
                  <SelectItem value="fullstack">풀스택 개발자</SelectItem>
                  <SelectItem value="data">데이터 엔지니어</SelectItem>
                  <SelectItem value="devops">DevOps 엔지니어</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="level">수준 *</Label>
              <Select value={level} onValueChange={setLevel}>
                <SelectTrigger id="level">
                  <SelectValue placeholder="수준 선택" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="junior">초급</SelectItem>
                  <SelectItem value="intermediate">중급</SelectItem>
                  <SelectItem value="senior">고급</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="competency">역량 유형 *</Label>
              <Select value={competency} onValueChange={setCompetency}>
                <SelectTrigger id="competency">
                  <SelectValue placeholder="역량 선택" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="spring">Spring Framework</SelectItem>
                  <SelectItem value="jpa">JPA/Hibernate</SelectItem>
                  <SelectItem value="security">보안 구현</SelectItem>
                  <SelectItem value="api">REST API 설계</SelectItem>
                  <SelectItem value="microservice">마이크로서비스</SelectItem>
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
              <Select value={questionType} onValueChange={setQuestionType}>
                <SelectTrigger id="type">
                  <SelectValue placeholder="유형 선택" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="multiple">객관식</SelectItem>
                  <SelectItem value="essay">서술형</SelectItem>
                  <SelectItem value="code">코드 작성</SelectItem>
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
                value={questionCount}
                onChange={(e) => setQuestionCount(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="difficulty">난이도 *</Label>
              <Select value={difficulty} onValueChange={setDifficulty}>
                <SelectTrigger id="difficulty">
                  <SelectValue placeholder="난이도 선택" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="easy">초급</SelectItem>
                  <SelectItem value="medium">중급</SelectItem>
                  <SelectItem value="hard">고급</SelectItem>
                  <SelectItem value="mixed">혼합</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="scope">문서 범위 (RAG)</Label>
              <Select value={documentScope} onValueChange={setDocumentScope}>
                <SelectTrigger id="scope">
                  <SelectValue placeholder="전체 문서" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">전체 문서</SelectItem>
                  <SelectItem value="spring">Spring 관련 문서만</SelectItem>
                  <SelectItem value="jpa">JPA 관련 문서만</SelectItem>
                  <SelectItem value="security">보안 관련 문서만</SelectItem>
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
          {generatedQuestions.length > 0 && (
            <>
              {/* Generation Summary */}
              <Card className="border-violet-200 bg-gradient-to-br from-violet-50 to-white">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Sparkles className="size-5 text-violet-600" />
                    생성 결과 요약
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-4 gap-4">
                    <div className="text-center">
                      <p className="text-2xl font-bold text-violet-700">
                        {generatedQuestions.length}
                      </p>
                      <p className="text-sm text-slate-600 mt-1">생성된 문제</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-green-700">
                        {generatedQuestions.filter((q) => q.validationStatus === "검증됨").length}
                      </p>
                      <p className="text-sm text-slate-600 mt-1">검증 통과</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-sky-700">
                        {Math.round(
                          generatedQuestions.reduce((acc, q) => acc + q.similarity, 0) /
                            generatedQuestions.length
                        )}
                        %
                      </p>
                      <p className="text-sm text-slate-600 mt-1">평균 유사도</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-amber-700">
                        {generatedQuestions[0]?.sourceReferences.length || 0}
                      </p>
                      <p className="text-sm text-slate-600 mt-1">참조 문서</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Question Cards */}
              {generatedQuestions.map((q) => (
                <Card key={q.id} className="border-slate-200">
                  <CardHeader className="border-b border-slate-100">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <CardTitle className="text-base font-medium text-slate-800">
                          {q.question}
                        </CardTitle>
                        <div className="flex items-center gap-2 mt-2">
                          {q.competencyTags.map((tag, idx) => (
                            <Badge key={idx} variant="secondary" className="bg-sky-100 text-sky-700">
                              {tag}
                            </Badge>
                          ))}
                          <Badge
                            variant="secondary"
                            className={
                              q.difficulty === "고급"
                                ? "bg-red-100 text-red-700"
                                : q.difficulty === "중급"
                                ? "bg-amber-100 text-amber-700"
                                : "bg-green-100 text-green-700"
                            }
                          >
                            {q.difficulty}
                          </Badge>
                        </div>
                      </div>
                      <Badge
                        variant="secondary"
                        className={
                          q.validationStatus === "검증됨"
                            ? "bg-green-100 text-green-700"
                            : "bg-amber-100 text-amber-700"
                        }
                      >
                        <CheckCircle2 className="size-3 mr-1" />
                        {q.validationStatus}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-4 space-y-4">
                    {/* Options */}
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-slate-700">선택지</p>
                      {q.options.map((option, idx) => (
                        <div
                          key={idx}
                          className={`p-3 rounded-lg border text-sm ${
                            option === q.correctAnswer
                              ? "bg-green-50 border-green-200"
                              : "bg-slate-50 border-slate-200"
                          }`}
                        >
                          <div className="flex items-start gap-2">
                            <span className="font-medium text-slate-600">{idx + 1}.</span>
                            <span className="flex-1 text-slate-700">{option}</span>
                            {option === q.correctAnswer && (
                              <Badge variant="secondary" className="bg-green-100 text-green-700">
                                정답
                              </Badge>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Explanation */}
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                      <p className="text-sm font-medium text-blue-900 mb-1">해설</p>
                      <p className="text-sm text-blue-800 leading-relaxed">{q.explanation}</p>
                    </div>

                    {/* Source Grounding */}
                    <div className="bg-violet-50 border border-violet-200 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <Database className="size-4 text-violet-700" />
                        <p className="text-sm font-medium text-violet-900">RAG 출처 검증</p>
                      </div>
                      <div className="space-y-1">
                        {q.sourceReferences.map((ref, idx) => (
                          <div key={idx} className="flex items-start gap-2">
                            <FileText className="size-3 text-violet-600 mt-0.5 flex-shrink-0" />
                            <p className="text-xs text-violet-800">{ref}</p>
                          </div>
                        ))}
                      </div>
                      <div className="mt-2 pt-2 border-t border-violet-200">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-violet-700">유사 문제 유사도</span>
                          <Badge
                            variant="secondary"
                            className={
                              q.similarity < 20
                                ? "bg-green-100 text-green-700"
                                : q.similarity < 40
                                ? "bg-amber-100 text-amber-700"
                                : "bg-red-100 text-red-700"
                            }
                          >
                            {q.similarity}%
                          </Badge>
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 pt-2">
                      <Button size="sm" className="bg-green-600 hover:bg-green-700">
                        <CheckCircle2 className="size-4 mr-2" />
                        승인 및 저장
                      </Button>
                      <Button size="sm" variant="outline">
                        <Save className="size-4 mr-2" />
                        임시 저장
                      </Button>
                      <Button size="sm" variant="outline">
                        <RotateCw className="size-4 mr-2" />
                        재생성
                      </Button>
                      <Button size="sm" variant="outline" className="text-red-600 hover:text-red-700">
                        <XCircle className="size-4 mr-2" />
                        거부
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </>
          )}

          {generatedQuestions.length === 0 && (
            <Card className="border-slate-200">
              <CardContent className="py-16 text-center">
                <Sparkles className="size-16 text-slate-300 mx-auto mb-4" />
                <p className="text-lg font-medium text-slate-700">AI 문제 생성 대기 중</p>
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
