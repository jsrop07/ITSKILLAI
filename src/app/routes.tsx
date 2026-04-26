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
