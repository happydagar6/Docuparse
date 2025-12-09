"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { generateCitation, getCitationFormats } from "@/lib/api";
import { toast } from "sonner";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "../ui/dropdown-menu";
import { Button } from "../ui/button";
import { Loader2 } from "lucide-react";
import { Quote } from "lucide-react";
import { ChevronDown } from "lucide-react";
import { Check } from "lucide-react";

export default function CitationButton({
  paperId,
  variant = "default",
  size = "default",
}) {
  const [copiedFormat, setCopiedFormat] = useState(null);

  const { data: formatsData } = useQuery({
    queryKey: ["citation-formats"],
    queryFn: getCitationFormats,
    staleTime: Infinity, // why Infinity? citation formats rarely change
  });

  const mutation = useMutation({
    mutationFn: ({ format }) => generateCitation(paperId, format),
    onSuccess: async (data, { format }) => {
      await navigator.clipboard.writeText(data.citation);
      setCopiedFormat(format);
      toast.success(`${format.toUpperCase()} citation copied!`);
      setTimeout(() => setCopiedFormat(null), 2500);
    },
    onError: () => toast.error("Failed to generate citation."),
  });

  const formats = formatsData?.formats || [
    { value: "apa", label: "APA" },
    { value: "ieee", label: "IEEE" },
    { value: "bibtex", label: "BibTeX" },
    { value: "vancouver", label: "Vancouver" },
    { value: "mla", label: "MLA" },
  ];


  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant={variant} size={size} disabled={mutation.isPending}>
          {mutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Quote className="h-4 w-4" />
          )}
          <span className="ml-2">Cite</span>
          <ChevronDown className="h-3 w-3 ml-1" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuLabel>Citation Format</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {formats.map((format) => (
          <DropdownMenuItem
            key={format.value}
            onClick={() => mutation.mutate({ format: format.value })}
            className="cursor-pointer"
          >
            <div className="flex items-center justify-between w-full">
              <span>{format.label}</span>
              {copiedFormat === format.value && (
                <Check className="h-4 w-4 text-green-500" />
              )}
            </div>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}