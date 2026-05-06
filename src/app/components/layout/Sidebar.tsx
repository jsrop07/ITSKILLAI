import { Link, useLocation, useNavigate } from "react-router";
import {
  LayoutDashboard,
  Users,
  ClipboardList,
  FolderKanban,
  HelpCircle,
  Sparkles,
  FileCheck,
  FileText,
  BarChart3,
  LogOut,
  ExternalLink,
} from "lucide-react";

const menuItems = [
  { icon: LayoutDashboard, label: "대시보드", path: "/" },
  { icon: Users, label: "응시자 관리", path: "/applicants" },
  { icon: ClipboardList, label: "시험 관리", path: "/exams" },
  { icon: HelpCircle, label: "문제 관리", path: "/questions" },
  { icon: Sparkles, label: "AI 문제 생성", path: "/ai-generation", highlight: true },
  { icon: FileCheck, label: "AI 문제 검토", path: "/ai-review", highlight: true },
  { icon: FileText, label: "문서/RAG 관리", path: "/documents" },
  { icon: BarChart3, label: "결과 분석", path: "/analytics" },
];

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("admin_token");
    navigate("/login");
  };

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col h-screen">
      <div className="p-6 border-b border-slate-200">
        <h1 className="text-xl font-semibold text-slate-800">IT 역량 평가</h1>
        <p className="text-sm text-slate-500 mt-1">관리자 콘솔</p>
      </div>

      <nav className="flex-1 p-4 overflow-y-auto">
        <ul className="space-y-1">
          {menuItems.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`
                    flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors
                    ${isActive
                      ? "bg-sky-50 text-sky-700"
                      : item.highlight
                        ? "text-slate-700 hover:bg-sky-50 hover:text-sky-600"
                        : "text-slate-600 hover:bg-slate-50"
                    }
                  `}
                >
                  <Icon className={`size-5 ${item.highlight && !isActive ? "text-sky-500" : ""}`} />
                  <span>{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>

        {/* 응시자 페이지 바로가기 */}
        <div className="mt-6 border-t border-slate-100 pt-4">
          <p className="text-xs text-slate-400 px-4 mb-2 font-medium uppercase tracking-wider">
            응시자 화면
          </p>
          <Link
            to="/apply"
            target="_blank"
            className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-slate-500 hover:bg-slate-50 transition-colors"
          >
            <ExternalLink className="size-4" />
            <span>시험 신청 페이지</span>
          </Link>
          <Link
            to="/test-login"
            target="_blank"
            className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-slate-500 hover:bg-slate-50 transition-colors"
          >
            <ExternalLink className="size-4" />
            <span>응시자 로그인</span>
          </Link>
        </div>
      </nav>

      <div className="p-4 border-t border-slate-200">
        <div className="flex items-center gap-3 px-2 mb-3">
          <div className="size-10 rounded-full bg-sky-100 flex items-center justify-center">
            <span className="text-sm font-medium text-sky-700">관</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-700 truncate">관리자</p>
            <p className="text-xs text-slate-500 truncate">jsrop07@naver.com</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-500 hover:bg-red-50 hover:text-red-600 transition-colors"
        >
          <LogOut className="size-4" />
          <span>로그아웃</span>
        </button>
      </div>
    </aside>
  );
}
