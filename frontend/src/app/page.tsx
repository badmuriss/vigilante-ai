import VideoFeed from "@/components/VideoFeed";
import StatusBar from "@/components/StatusBar";
import Controls from "@/components/Controls";
import AlertPanel from "@/components/AlertPanel";

export default function Home() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Monitoramento</h2>
        <Controls />
      </div>
      <StatusBar />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <VideoFeed />
        </div>
        <div className="lg:col-span-1">
          <AlertPanel />
        </div>
      </div>
    </div>
  );
}
