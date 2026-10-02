import type { CognitoUser } from "amazon-cognito-identity-js";

const USER_POOL_ID = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID ?? "";
const CLIENT_ID = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ?? "";

export const cognitoConfigured = Boolean(USER_POOL_ID && CLIENT_ID);

export type IdTokenClaims = Record<string, unknown>;

export type SignInOutcome =
  | { kind: "success"; claims: IdTokenClaims; signOut: () => void }
  | {
      kind: "new_password";
      complete: (newPassword: string) => Promise<SignInOutcome>;
    };

const ERROR_MESSAGES: Record<string, string> = {
  NotAuthorizedException: "Usuario o contraseña incorrectos.",
  UserNotFoundException: "Usuario o contraseña incorrectos.",
  PasswordResetRequiredException:
    "Debes restablecer tu contraseña antes de ingresar.",
  UserNotConfirmedException: "Tu usuario aún no está confirmado.",
  InvalidPasswordException:
    "La nueva contraseña no cumple la política: mínimo 8 caracteres, con mayúsculas, minúsculas, números y símbolos.",
  TooManyRequestsException: "Demasiados intentos. Espera un momento e intenta de nuevo.",
  LimitExceededException: "Demasiados intentos. Espera un momento e intenta de nuevo.",
};

export function cognitoErrorMessage(err: unknown): string {
  const e = err as { code?: string; name?: string; message?: string };
  const key = e?.code || e?.name || "";
  if (ERROR_MESSAGES[key]) {
    if (key === "NotAuthorizedException" && /expired|temporary/i.test(e.message ?? "")) {
      return "Tu contraseña temporal expiró. Solicita una nueva al banco.";
    }
    return ERROR_MESSAGES[key];
  }
  if (e?.message && /network|fetch/i.test(e.message)) {
    return "No pudimos conectarnos con el servicio de autenticación. Revisa tu conexión.";
  }
  return e?.message || "No pudimos iniciar tu sesión.";
}

function callbacks(
  user: CognitoUser,
  resolve: (o: SignInOutcome) => void,
  reject: (e: unknown) => void,
) {
  return {
    onSuccess: (session: { getIdToken: () => { decodePayload: () => IdTokenClaims } }) =>
      resolve({
        kind: "success",
        claims: session.getIdToken().decodePayload(),
        signOut: () => user.signOut(),
      }),
    onFailure: reject,
    newPasswordRequired: () =>
      resolve({
        kind: "new_password",
        complete: (newPassword: string) =>
          new Promise<SignInOutcome>((res, rej) =>
            user.completeNewPasswordChallenge(newPassword, {}, callbacks(user, res, rej)),
          ),
      }),
  };
}

export async function signIn(username: string, password: string): Promise<SignInOutcome> {
  const { AuthenticationDetails, CognitoUser, CognitoUserPool } = await import(
    "amazon-cognito-identity-js"
  );
  const pool = new CognitoUserPool({ UserPoolId: USER_POOL_ID, ClientId: CLIENT_ID });
  const user = new CognitoUser({ Username: username, Pool: pool });
  const details = new AuthenticationDetails({ Username: username, Password: password });
  return new Promise<SignInOutcome>((resolve, reject) =>
    user.authenticateUser(details, callbacks(user, resolve, reject)),
  );
}
