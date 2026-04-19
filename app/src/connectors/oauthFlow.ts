import { Platform } from "react-native";
import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";

WebBrowser.maybeCompleteAuthSession();

/**
 * URL Google OAuth will return the user to after our backend finishes the callback
 * (server redirects here with ?connector_status=...).
 */
export function getConnectorReturnUrl(): string {
  if (Platform.OS === "web" && typeof window !== "undefined") {
    return `${window.location.origin}/`;
  }
  return Linking.createURL("connectors/callback");
}

export type OpenConnectorAuthOptions = {
  /**
   * iOS: prefer an ephemeral web session so a prior Notion login in Safari
   * is less likely to auto-approve the wrong account (no effect on Android/web).
   */
  preferEphemeralSession?: boolean;
};

/**
 * Open the provider consent screen. On web, full-page navigation; on native, in-app browser.
 */
export async function openConnectorAuthorizationUrl(
  authorizationUrl: string,
  options?: OpenConnectorAuthOptions
): Promise<void> {
  if (Platform.OS === "web") {
    window.location.href = authorizationUrl;
    return;
  }
  const returnUrl = getConnectorReturnUrl();
  await WebBrowser.openAuthSessionAsync(authorizationUrl, returnUrl, {
    preferEphemeralSession: options?.preferEphemeralSession === true,
  });
}
