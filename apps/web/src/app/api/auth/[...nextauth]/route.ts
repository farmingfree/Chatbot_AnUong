import NextAuth from 'next-auth'
import GoogleProvider from 'next-auth/providers/google'

export const authOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    })
  ],
  callbacks: {
    async jwt({ token, account, profile }: any) {
      if (account) {
        token.email = profile?.email
        token.name = profile?.name
        token.picture = profile?.picture
      }
      return token
    },
    async session({ session, token }: any) {
      session.user.email = token.email as string
      return session
    }
  },
  secret: process.env.NEXTAUTH_SECRET,
}

const handler = NextAuth(authOptions)
export { handler as GET, handler as POST }
