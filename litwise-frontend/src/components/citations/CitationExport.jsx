"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { generateBatchCitations, exportBibTeX } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from "../ui/dialog";
import { Button } from "../ui/button";
import { FileText } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Loader2 } from "lucide-react";
import { Copy } from "lucide-react";
import { Download } from "lucide-react";


const FORMATS = [
    { value: 'apa', label: 'APA 7th Edition' },
  { value: 'ieee', label: 'IEEE' },
  { value: 'bibtex', label: 'BibTeX' },
  { value: 'vancouver', label: 'Vancouver' },
  { value: 'mla', label: 'MLA 9th Edition' },
];

export default function CitationExport({ paperIds, trigger }) {
    const [open, setOpen] = useState(false);
    const [format, setFormat] = useState("apa");
    const [citations, setCitations] = useState([]);

    const batchMutation = useMutation({
        mutationFn: () => generateBatchCitations(paperIds, format),
        onSuccess: (data) => {
            setCitations(data.citations);
            toast.success(`Generated ${data.citations.length} citations`);
        },
        onError: () => toast.error("Failed to generate citations."),
    });

    const bibtexMutation = useMutation({
        mutationFn: () => exportBibTeX(paperIds),
        onSuccess: (data) => {
            const blob = new Blob([data], { type: "text/plain" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "references.bib";
            a.click();
            URL.revokeObjectURL(url);
            toast.success("BibTeX file downloaded!");
        },
        onError: () => toast.error("Failed to export BibTeX."),
    });

    const copyAll = async () => {
        const text = citations.map((c) => c.citation).join("\n\n");
        await navigator.clipboard.writeText(text);
        toast.success("All citations copied to clipboard!");
    };

    const downloadTxt = () => {
        const text = citations.map((c) => c.citation).join("\n\n");
        const blob = new Blob([text], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `references_${format}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success("Citations file downloaded!");
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" size="sm">
            <FileText className="h-4 w-4 mr-2" />
            Export Citations ({paperIds.length})
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Export Citations</DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground mt-1">
            Export your citations in multiple formats (APA, MLA, Chicago, BibTeX)
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Format Selection */}
          <div className="flex gap-2">
            <Select value={format} onValueChange={setFormat}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {FORMATS.map((f) => (
                  <SelectItem key={f.value} value={f.value}>
                    {f.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button onClick={() => batchMutation.mutate()} disabled={batchMutation.isPending}>
              {batchMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                'Generate'
              )}
            </Button>
          </div>

          {/* Generated Citations */}
          {citations.length > 0 && (
            <>
              <div className="border rounded-lg p-4 bg-muted/50 max-h-64 overflow-y-auto">
                {citations.map((c, i) => (
                  <div key={c.paper_id} className="mb-4 last:mb-0">
                    <p className="text-xs text-muted-foreground mb-1">{c.title}</p>
                    <p className="text-sm">{c.citation}</p>
                    {i < citations.length - 1 && <hr className="mt-4" />}
                  </div>
                ))}
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2">
                <Button onClick={copyAll} variant="outline">
                  <Copy className="h-4 w-4 mr-2" />
                  Copy All
                </Button>
                <Button onClick={downloadTxt} variant="outline">
                  <Download className="h-4 w-4 mr-2" />
                  Download .txt
                </Button>
                {format === 'bibtex' && (
                  <Button
                    onClick={() => bibtexMutation.mutate()}
                    disabled={bibtexMutation.isPending}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download .bib
                  </Button>
                )}
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}