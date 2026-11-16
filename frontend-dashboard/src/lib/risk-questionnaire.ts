
import { z } from "zod";

// Defines which answers are allowed
export const riskQuestionnaireSchema = z.object({
  horizon: z.enum(["lt1", "1to3", "3to5", "gt5"]),
  affordableLoss: z.enum(["none", "up10", "up25", "over25"]),
  marketDrop: z.enum(["sell", "hold", "buy"]),
  experience: z.enum(["beginner", "some", "experienced"]),
  goal: z.enum(["preserve", "balanced", "growth"]),
}).strict();

// TypeScript type of the submitted answers
export type RiskAnswers =
  z.infer<typeof riskQuestionnaireSchema>;

// Questions displayed to the user
export const riskQuestions = [
  {
    id: "horizon",
    question: "What is your investment time horizon?",
    options: [
      { value: "lt1", label: "Less than 1 year" },
      { value: "1to3", label: "1–3 years" },
      { value: "3to5", label: "3–5 years" },
      { value: "gt5", label: "More than 5 years" },
    ],
  },
  {
    id: "affordableLoss",
    question: "How much of your invested money could you financially afford to lose?",
    options: [
      { value: "none", label: "None" },
      { value: "up10", label: "Up to 10%" },
      { value: "up25", label: "Up to 25%" },
      { value: "over25", label: "More than 25%" },
    ],
  },
  {
    id: "marketDrop",
    question: "If your portfolio lost 20%, what would you do?",
    options: [
      { value: "sell", label: "Sell to prevent further losses" },
      { value: "hold", label: "Hold and wait for recovery" },
      { value: "buy", label: "Consider buying more" },
    ],
  },
  {
    id: "experience",
    question: "How experienced are you with investing?",
    options: [
      { value: "beginner", label: "Beginner" },
      { value: "some", label: "Some experience" },
      { value: "experienced", label: "Experienced investor" },
    ],
  },
  {
    id: "goal",
    question: "What is your primary investment objective?",
    options: [
      { value: "preserve", label: "Preserve my capital" },
      { value: "balanced", label: "Balance growth and stability" },
      { value: "growth", label: "Maximize long-term growth" },
    ],
  },
] satisfies {
  id: keyof RiskAnswers;
  question: string;
  options: { value: string; label: string }[];
}[];
