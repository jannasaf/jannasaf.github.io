import source from "./portfolio.json";

export const portfolio = source;

const slugByShortId: Record<string, string> = {
  d54c8b60: "concierj",
  bcec2b9d: "digital-giving",
  d97079f4: "workflow-automation"
};

const titleByShortId: Record<string, string> = {
  d97079f4: "Reducing Project Setup Time Through Workflow Automation"
};

const metaByShortId: Record<string, string> = {
  d54c8b60:
    "A 0-to-1 AI-powered pre-booking communications and guest intelligence product for boutique hotels.",
  bcec2b9d:
    "How user research and a redesigned giving funnel reduced donor abandonment by 63% and strengthened long-term engagement.",
  d97079f4:
    "How workflow automation reduced project setup time from two hours to under 30 seconds."
};

export function plainText(html = "") {
  return html
    .replace(/<br\s*\/?>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&nbsp;/g, " ")
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/\s+/g, " ")
    .trim();
}

const copyFixes: Array<[RegExp, string]> = [
  [/\bore capabilities\b/g, "core capabilities"],
  [/\bConcerj\b/g, "Concierj"],
  [/\bguest-decison\b/g, "guest-decision"],
  [/\bexpeirence\b/g, "experience"],
  [/\bi developed specialized\b/g, "I developed specialized"],
  [/\bThe assistant become\b/g, "The assistant became"],
  [/\bminimalizing\b/g, "minimizing"],
  [/\bdirectly do a third-party form\b/g, "directly to a third-party form"],
  [/\bsocially sharable\b/g, "socially shareable"],
  [/\bhelped shaped\b/g, "helped shape"],
  [/Safe Water Network \.In/g, "Safe Water Network. In"],
  [
    /became trapped in an error state failed to continue/g,
    "became trapped in an error state, failed to continue"
  ],
  [
    /This reduced project setup went from two hours to under 30 seconds\./g,
    "This reduced project setup time from two hours to under 30 seconds."
  ]
];

export function cleanHtml(html = "") {
  return copyFixes.reduce(
    (result, [pattern, replacement]) => result.replace(pattern, replacement),
    html
  );
}

export function localAsset(url?: string | null) {
  if (!url) return "";
  if (
    url.startsWith("/example_project_images/") ||
    url.startsWith("/placeholder-images/")
  ) {
    return "";
  }
  if (!url.includes("uxfolio-prod.s3.us-east-1.amazonaws.com")) return url;
  const filename = decodeURIComponent(url.split("/").at(-1)?.split("?")[0] ?? "");
  return `/assets/portfolio/${filename}`;
}

export function isValidMedia(url?: string | null) {
  return Boolean(localAsset(url));
}

export function sectionTitle(section: any) {
  return plainText(section.title || section.text || "") || "Project visual";
}

export const projects = portfolio.projects.map((project: any) => {
  const mainHeader = project.sections.find(
    (section: any) => section.type === "MainHeader"
  );
  const title =
    project.name ||
    titleByShortId[project.shortId] ||
    plainText(mainHeader?.title) ||
    "Case study";

  return {
    ...project,
    title,
    slug: slugByShortId[project.shortId] || project.shortId,
    description:
      metaByShortId[project.shortId] ||
      plainText(mainHeader?.subtitle) ||
      project.subtitle,
    socialImage:
      project.socialImage ||
      mainHeader?.media?.url ||
      project.thumbnailImages?.[0] ||
      null
  };
});

export function getProject(slug: string) {
  return projects.find((project) => project.slug === slug);
}

export const homePage = portfolio.pages.find(
  (page: any) => page.shortId === "home"
);

export const aboutPage = portfolio.pages.find(
  (page: any) => page.name === "About"
);
