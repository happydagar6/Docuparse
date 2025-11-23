"use client";

import { useMutation } from "@tanstack/react-query";
import { Button } from "./ui/button";

async function uploadpaper(formData) {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Failed to upload paper");
  return res.json();
}

export default function UploadForm() {
  const mutation = useMutation({ mutationFn: uploadpaper });

  const handleSubmit = (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    mutation.mutate(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <input
        name="title"
        placeholder="Paper Title"
        className="border p-2 w-full"
      />
      <input
        type="file"
        name="file"
        accept=".pdf"
        className="border p-2 w-full"
      />
      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? "Uploading..." : "Upload PDF"}
      </Button>
      {mutation.data && <p>Uploaded! ID: {mutation.data.id}</p>}
    </form>
  );
}
