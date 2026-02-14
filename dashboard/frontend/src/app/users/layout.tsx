import ChatWidgetWrapper from "@/components/ChatWidgetWrapper";

export default function UsersLayout({
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
