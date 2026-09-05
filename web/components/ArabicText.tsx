"use client";

const ARABIC = /[\u0600-\u06FF]/;

export function hasArabic(text: string | null | undefined): boolean {
  return Boolean(text && ARABIC.test(text));
}

export function ArabicText({
  text,
  textEn,
  language,
}: {
  text: string;
  textEn?: string | null;
  language?: string | null;
}) {
  const arabic = language === "ar" || language === "mixed" || hasArabic(text);
  return (
    <div className="max-w-[75ch] space-y-1">
      <p
        className={arabic ? "font-ar text-body text-fg" : "text-body text-fg"}
        dir={arabic ? "rtl" : "ltr"}
        style={{ textAlign: arabic ? "right" : "left" }}
      >
        {text}
      </p>
      {arabic && textEn ? (
        <p className="text-body text-fg-2" dir="ltr">
          EN: {textEn}
        </p>
      ) : null}
    </div>
  );
}
