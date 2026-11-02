package br.com.sat.torcedor;

import android.app.DownloadManager;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.webkit.CookieManager;
import android.webkit.URLUtil;
import android.widget.Toast;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // O WebView não baixa arquivos sozinho: as planilhas (CSV) do site vão para a pasta Downloads,
        // levando o cookie da sessão para o servidor saber quem está logado.
        getBridge().getWebView().setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> {
            String nome = URLUtil.guessFileName(url, contentDisposition, mimeType);
            DownloadManager.Request pedido = new DownloadManager.Request(Uri.parse(url))
                .setMimeType(mimeType)
                .addRequestHeader("User-Agent", userAgent)
                .setTitle(nome)
                .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, nome);
            String cookies = CookieManager.getInstance().getCookie(url);
            if (cookies != null) {
                pedido.addRequestHeader("Cookie", cookies);
            }
            ((DownloadManager) getSystemService(DOWNLOAD_SERVICE)).enqueue(pedido);
            Toast.makeText(this, "Baixando " + nome, Toast.LENGTH_SHORT).show();
        });
    }
}
