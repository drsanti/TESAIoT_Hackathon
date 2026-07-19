import type { ReactNode } from "react";

export type TutorialCheck = {
  id: string;
  label: string;
  pass: boolean;
};

export type TutorialStepDef = {
  id: string;
  title: string;
  /** Short teaching prose (Why). */
  why: ReactNode;
  /** Interactive controls (Do). */
  do?: ReactNode;
  /** Live acceptance criteria (Check). */
  checks: TutorialCheck[];
  /** Optional tip / warn under the step. */
  callout?: ReactNode;
};

export type ChapterMeta = {
  id: string;
  path: string;
  title: string;
  blurb: string;
};
