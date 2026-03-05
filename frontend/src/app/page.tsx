"use client";

import { useState, useEffect, useCallback } from "react";
import VideoFeed from "@/components/VideoFeed";
import StatusBar from "@/components/StatusBar";
import Controls from "@/components/Controls";
import AlertPanel from "@/components/AlertPanel";
import EPIPanel from "@/components/EPIPanel";
import { getStatus } from "@/lib/api";
import type { SystemStatus } from "@/types";

export default function Home() {
  const [isRunning, setIsRunning] = useState(false);
  const [status, setStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    const fetchStatus = () => {
      getStatus()
        .then((s) => {
          setStatus(s);
          setIsRunning(s.camera_active);
        })
        .catch(() => {
          setStatus(null);
          setIsRunning(false);
        });
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleStart = useCallback(() => {
    setIsRunning(true);
  }, []);

  const handleStop = useCallback(() => {
    setIsRunning(false);
  }, []);

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-xl font-semibold">Monitoramento</h2>
          <StatusBar status={status} isRunning={isRunning} />
        </div>
        <Controls isRunning={isRunning} onStart={handleStart} onStop={handleStop} />
      </div>

      {/* Main grid: EPIPanel | VideoFeed | AlertPanel */}
      <div className="flex flex-col gap-4 lg:flex-row">
        <div className="w-full shrink-0 lg:w-56">
          <EPIPanel />
        </div>
        <div className="min-w-0 flex-1">
          <VideoFeed isRunning={isRunning} />
        </div>
        <div className="w-full shrink-0 lg:w-80">
          <AlertPanel />
        </div>
      </div>
    </div>
  );
}
