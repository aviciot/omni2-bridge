import ChatWidgetWrapper from "@/components/ChatWidgetWrapper";

export default function AnalyticsLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <>
      {children}
      <ChatWidgetWrapper />
    </>
  );
}
