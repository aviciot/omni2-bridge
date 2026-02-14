import ChatWidgetWrapper from "@/components/ChatWidgetWrapper";

export default function McpsLayout({
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
