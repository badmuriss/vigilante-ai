import VideoFeed from "@/components/VideoFeed";
import StatusBar from "@/components/StatusBar";
import Controls from "@/components/Controls";

export default function Home() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Monitoramento</h2>
        <Controls />
      </div>
      <StatusBar />
      <VideoFeed />
    </div>
  );
}
