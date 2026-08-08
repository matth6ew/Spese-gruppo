if not settlements:
            st.markdown(
                '<div class="empty-success">✓ Tutti i conti sono perfettamente in pari.</div>',
                unsafe_allow_html=True,
            )
        else:
            for s in settlements:
                with st.container(border=True):
                    cols = st.columns([2, 0.5, 2, 1.5])
                    with cols[0]:
                        st.caption("DEVE PAGARE")
                        st.markdown(f"🔴 **{s['from']}**")
                    with cols[1]:
                        st.markdown("<div style='text-align: center; font-size: 1.2rem; padding-top: 10px;'>→</div>", unsafe_allow_html=True)
                    with cols[2]:
                        st.caption("RICEVE")
                        st.markdown(f"🟢 **{s['to']}**")
                    with cols[3]:
                        st.markdown("<div style='text-align: right; padding-top: 10px;'>", unsafe_allow_html=True)
                        st.markdown(f"**{euro(s['amount'])}**")
                        st.markdown("</div>", unsafe_allow_html=True)
