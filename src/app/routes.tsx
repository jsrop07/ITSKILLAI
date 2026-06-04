import { createBrowserRouter } from "react-router";

// Admin pages
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import ApplicantManagement from "./pages/ApplicantManagement";
import ApplicantDetail from "./pages/ApplicantDetail";
import ExamManagement from "./pages/ExamManagement";
import ExamForm from "./pages/ExamForm";
import QuestionManagement from "./pages/QuestionManagement";
import AIQuestionGeneration from "./pages/AIQuestionGeneration";
import AIQuestionReview from "./pages/AIQuestionReview";
import DocumentRAGManagement from "./pages/DocumentRAGManagement";
import ResultAnalytics from "./pages/ResultAnalytics";
import MainLayout from "./components/layout/MainLayout";

// Applicant pages
import Apply from "./pages/applicant/Apply";
import TestLogin from "./pages/applicant/TestLogin";
import TestIntro from "./pages/applicant/TestIntro";
import TestRoom from "./pages/applicant/TestRoom";
import TestSubmit from "./pages/applicant/TestSubmit";
import TestResult from "./pages/applicant/TestResult";

// Direct pages
import DirectAssessmentLogin from "./pages/direct-assessment/DirectAssessmentLogin";
import DirectAssessmentExamList from "./pages/direct-assessment/DirectAssessmentExamList";
import DirectAssessmentTake from "./pages/direct-assessment/DirectAssessmentTake";
import DirectAssessmentResult from "./pages/direct-assessment/DirectAssessmentResult";

export const router = createBrowserRouter([
  // ─────────────────────────────────────────
  // 응시자 공개 페이지 (레이아웃 없음)
  // ─────────────────────────────────────────
  { path: "/apply", Component: Apply },
  { path: "/test-login", Component: TestLogin },
  { path: "/test-intro", Component: TestIntro },
  { path: "/test-room", Component: TestRoom },
  { path: "/test-submit", Component: TestSubmit },
  { path: "/test-result", Component: TestResult },

  {
    path: "/direct-assessment",
    element: <DirectAssessmentLogin />,
  },
  {
    path: "/direct-assessment/login",
    element: <DirectAssessmentLogin />,
  },
  {
    path: "/direct-assessment/exams",
    element: <DirectAssessmentExamList />,
  },
  {
    path: "/direct-assessment/take/:recordId",
    element: <DirectAssessmentTake />,
  },
  {
    path: "/direct-assessment/result/:recordId",
    element: <DirectAssessmentResult />,
  },

  // ─────────────────────────────────────────
  // 관리자 영역 (사이드바 레이아웃)
  // ─────────────────────────────────────────
  {
    path: "/login",
    Component: Login,
  },
  {
    path: "/",
    Component: MainLayout,
    children: [
      { index: true, Component: Dashboard },
      { path: "applicants", Component: ApplicantManagement },
      { path: "applicants/:id", Component: ApplicantDetail },
      { path: "exams", Component: ExamManagement },
      { path: "exams/new", Component: ExamForm },
      { path: "exams/:id", Component: ExamForm },
      { path: "questions", Component: QuestionManagement },
      { path: "ai-generation", Component: AIQuestionGeneration },
      { path: "ai-review", Component: AIQuestionReview },
      { path: "documents", Component: DocumentRAGManagement },
      { path: "analytics", Component: ResultAnalytics },
    ],
  },
]);
