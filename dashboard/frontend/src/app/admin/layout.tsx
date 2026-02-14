import ChatWidgetWrapper from "@/components/ChatWidgetWrapper";

export default function AdminLayout({
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
