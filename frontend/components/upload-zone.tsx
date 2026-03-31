"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileText, Loader2 } from "lucide-react";
import { uploadCSV } from "@/lib/api";
import { cn } from "@/lib/utils";

export function UploadZone() {
  const router = useRouter();
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.endsWith(".csv")) {
        setError("Please upload a CSV file.");
        return;
      }
      setError(null);
      setIsUploading(true);
      try {
        const { job_id } = await uploadCSV(file);
        router.push(`/jobs/${job_id}`);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Upload failed");
        setIsUploading(false);
      }
    },
    [router]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="w-full">
      <label
        htmlFor="csv-upload"
        className={cn(
          "flex flex-col items-center justify-center w-full h-48 border-2 border-dashed rounded-lg cursor-pointer transition-all",
          isDragging
            ? "border-accent bg-accent/5"
            : "border-border hover:border-accent/50 hover:bg-muted/50",
          isUploading && "pointer-events-none opacity-60"
        )}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
      >
        <div className="flex flex-col items-center gap-3 px-4 text-center">
          {isUploading ? (
            <>
              <Loader2 className="w-10 h-10 text-accent animate-spin" />
              <p className="text-sm text-muted-foreground">Uploading and parsing CSV...</p>
            </>
          ) : (
            <>
              <div className="p-3 rounded-full bg-muted border border-border">
                {isDragging ? (
                  <FileText className="w-7 h-7 text-accent" />
                ) : (
                  <Upload className="w-7 h-7 text-muted-foreground" />
                )}
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">
                  {isDragging ? "Drop your CSV here" : "Drag & drop your Spiritory KPI CSV"}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  or click to browse — must contain a{" "}
                  <code className="text-accent">whiskybaseID</code> column
                </p>
              </div>
            </>
          )}
        </div>
        <input
          id="csv-upload"
          type="file"
          accept=".csv"
          className="hidden"
          onChange={onInputChange}
          disabled={isUploading}
        />
      </label>
      {error && (
        <p className="mt-2 text-sm text-destructive text-center">{error}</p>
      )}
    </div>
  );
}
