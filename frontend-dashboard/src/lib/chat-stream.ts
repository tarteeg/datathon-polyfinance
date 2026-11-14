export type ChatActivity = {
  id: string;
  tool: string;
  input: Record<string, unknown>;
  status: "running" | "completed" | "partial" | "failed";
};

// HTTP chunks may split a UTF-8 character or contain several newline-delimited records.
export async function* readChatStream(response: Response) {
  if (!response.body) throw new Error("Empty chat stream.");
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += value;
      let end = buffer.indexOf("\n");
      while (end !== -1) {
        const line = buffer.slice(0, end);
        buffer = buffer.slice(end + 1);
        yield JSON.parse(line);
        end = buffer.indexOf("\n");
      }
    }
    if (buffer) throw new Error("Incomplete chat stream.");
  } finally {
    await reader.cancel();
    reader.releaseLock();
  }
}

// Older turns could include a simulated tool transcript with unverified prices.
export function savedChatAnswer(answer: string) {
  if (/^\s*(?:Tool (?:calls?|responses?):|\[Calling (?:get_stock|compare_stocks)\b)/im.test(answer)) {
    return "This earlier reply included unverified tool output. Ask again to fetch the historical prices.";
  }
  return answer;
}
