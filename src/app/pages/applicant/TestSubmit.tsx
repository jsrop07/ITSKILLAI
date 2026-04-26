import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import { CheckCircle, Clock, Eye } from "lucide-react";

export default function TestSubmit() {
  const navigate = useNavigate();
  const [recordId, setRecordId] = useState<string | null>(null);

  useEffect(() => {
    const id = sessionStorage.getItem("submitted_record_id");
    if (!id) { navigate("/test-login"); return; }
    setRecordId(id);
    // session 정리
    sessionStorage.removeItem("exam_session");
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-sky-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full space-y-6">
        <Card className="shadow-xl border-slate-200 overflow-hidden">
          {/* Green banner */}
          <div className="bg-gradient-to-r from-green-500 to-emerald-500 p-8 text-center">
            <div className="mx-auto size-20 rounded-full bg-white/20 flex items-center justify-center mb-4">
              <CheckCircle className="size-12 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white">제출 완료!</h1>
            <p className="text-green-100 mt-2">시험이 성공적으로 제출되었습니다.</p>
          </div>

          <CardContent className="pt-6 pb-8 space-y-5 text-center">
            <div className="space-y-2">
              <p className="text-slate-700 font-medium">수고하셨습니다!</p>
              <p className="text-sm text-slate-500 leading-relaxed">
                채점이 완료되면 결과를 확인하실 수 있습니다.<br />
                결과 공개 여부는 담당자가 결정하며,<br />
                공개 시 아래 버튼을 통해 확인하실 수 있습니다.
              </p>
            </div>

            <div className="bg-slate-50 rounded-xl p-4 flex items-center gap-3 text-left">
              <div className="size-10 rounded-full bg-sky-100 flex items-center justify-center flex-shrink-0">
                <Clock className="size-5 text-sky-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-700">결과 확인 안내</p>
                <p className="text-xs text-slate-500">담당자가 결과를 공개하면 아래 버튼이 활성화됩니다.</p>
              </div>
            </div>

            <div className="flex flex-col gap-3 pt-2">
              {recordId && (
                <Button
                  className="w-full bg-sky-600 hover:bg-sky-700"
                  onClick={() => navigate(`/test-result?record_id=${recordId}`)}
                >
                  <Eye className="size-4 mr-2" />
                  결과 확인하기
                </Button>
              )}
              <Button
                variant="outline"
                className="w-full"
                onClick={() => navigate("/apply")}
              >
                메인으로 돌아가기
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
