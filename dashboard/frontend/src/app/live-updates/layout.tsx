import ChatWidgetWrapper from "@/components/ChatWidgetWrapper";

export default function LiveUpdatesLayout({
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
