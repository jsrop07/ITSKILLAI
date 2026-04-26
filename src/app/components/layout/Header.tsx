import { Bell, Settings, LogOut } from "lucide-react";
import { Button } from "../ui/button";
import { useNavigate } from "react-router";

export default function Header() {
  const navigate = useNavigate();

  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6">
      <div className="flex-1">
        <h2 className="text-lg font-semibold text-slate-800">AI 기반 IT 역량 평가 플랫폼</h2>
      </div>
      
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" className="text-slate-600 hover:text-slate-800">
          <Bell className="size-5" />
        </Button>
        <Button variant="ghost" size="icon" className="text-slate-600 hover:text-slate-800">
          <Settings className="size-5" />
        </Button>
        <div className="h-6 w-px bg-slate-200 mx-2" />
        <Button
          variant="ghost"
          size="sm"
          className="text-slate-600 hover:text-slate-800"
          onClick={() => navigate("/login")}
        >
          <LogOut className="size-4 mr-2" />
          로그아웃
        </Button>
      </div>
    </header>
  );
}
